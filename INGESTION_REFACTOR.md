# Ingestion & transformation refactor — design notes

> **Status:** local scratch doc, not committed. Branch
> `feat/optimize-data-manipulation-memory-and-throughput`.
> Captures the *why* behind the four commits on top of
> `e2ca99ba`, and how this approach compares to the alternative
> `origin/use-gdal` (ogr2ogr) branch.

## Problem

Downloading, reading, transforming and writing a dataset all happened in
Python memory via geopandas/pandas:

- `gpd.read_file` / `gpd.read_postgis` materialised the **whole** dataset as a
  GeoDataFrame; `to_postgis` wrote it back row-by-row through SQLAlchemy.
- the staging→final transform read everything into pandas, applied
  rename/cast/projection, and wrote it back — a full double trip.
- HTTP/upload bodies were buffered entirely (`response.content`,
  `await file.read()`).

Peak memory therefore scaled with file size, and large datasets were slow or
OOM-prone.

## Approach: keep the data out of Python

Two independent ideas, one per side of the pipe.

### 1. Transformation runs in PostGIS (never enters Python)

`transformation/transform_sql.py` builds **one** canonical SQLAlchemy Core
`SELECT` (`build_transformation_select`) expressing column select/exclude,
rename, cast, ILIKE filters and geometry construction. That single query feeds:

- **process path** — `transform_staging_to_final`:
  `CREATE TABLE final AS <select>`, then `id_datafeeder` PK + GIST index, all in
  one transaction. Returns the row count from SQL.
- **preview path** — `read_transformed_preview`: the same select wrapped with
  `LIMIT`, geometry serialised in the database (`ST_AsText` for the table,
  `ST_AsGeoJSON(ST_Transform(..,4326))` for the map).

Because both paths compile the *same* builder, preview and final output cannot
drift — that consistency is structural, not maintained by hand.

### 2. Ingestion streams Arrow batches → ADBC bulk load

- `arrow_reader.py` yields bounded `pyarrow.RecordBatch`es from:
  - **files / WFS / OAPIF** via `pyogrio.raw.open_arrow` (GDAL under the hood,
    but as a *wheel*, not a system binary),
  - **(Geo)Parquet** via `pyarrow.parquet`,
  - **db→db** via a SQLAlchemy server-side cursor (`stream_results` +
    `partitions`).
  Geometry stays **raw WKB bytes** the whole way — no shapely objects.
- `postgis_writer.py` loads each batch with
  `adbc_ingest(mode="replace")` (COPY BINARY under the hood) into a binary
  `geom` column, then runs **one** `ALTER COLUMN … TYPE geometry USING
  ST_GeomFromWKB(…)` + `CREATE INDEX … GIST`, and commits. All inside a single
  transaction.

Peak memory is now bounded by the batch size (`BATCH_ROWS = 50_000`),
independent of dataset size. A streaming RSS benchmark
(`tests/bench/test_streaming_rss.py`) guards against regressions.

## Key decisions & rationale

| Decision | Rationale |
|---|---|
| **pip-only, no system GDAL** | `pyogrio`, `pyarrow`, `pyproj`, `adbc-driver-postgresql` all ship manylinux wheels. The official `gdal` PyPI package is **source-only** (needs `gdal-config` + headers), which is exactly what forces the conda/Docker route — avoided. |
| **ADBC for writes, not `ogr2ogr -f PostgreSQL`** | Stays in-process (no subprocess, no credentials in `argv`/`/proc`), driver-agnostic over psycopg2 (Airflow) and psycopg3 (backend), and Arrow-native so geometry never round-trips through text. |
| **Fix the dropped-filter blocker via `exec_driver_sql(ctas, compiled.params)`** | The prior code string-spliced the WHERE after `rfind(" WHERE ")`, which never matched SQLAlchemy's `\nWHERE`, so filters were silently dropped from final tables while still applied in preview. Compiling once and passing DBAPI-native params keeps every value bound (no injection) and the WHERE intact. A regression test asserts both. |
| **Inline CASE-expression casts**, not plpgsql helper functions | Keeps casts as pure SQL fragments inside the SELECT — no `CREATE FUNCTION` DDL on `public`, no per-row plpgsql subtransaction (which on a multi-million-row CTAS is slow and burns XIDs). |
| **Schema fixed from source metadata** (not inferred from batch 1) | OGR/Parquet metadata defines the Arrow schema up front, so an int column whose nulls only appear in a later batch can't silently coerce to float and break the load. |
| **force_projection = `ST_Transform`** (reproject), with `ST_SetSRID` fallback at SRID 0 | Product decision: the picker reprojects coordinates. SRID 0 means the source CRS is unknown, so there is nothing to reproject *from* — we label in place instead of erroring. |
| **Single transaction, `mode="replace"`** | Drop+recreate+load+fixup either all commit or all roll back; a mid-stream failure leaves the previous staging table intact. Same guarantee as the old `to_postgis(if_exists="replace")`, no temp-table dance. |
| **Restore the GIST index** | `to_postgis` created it implicitly; the SQL CTAS path must do it explicitly or spatial queries regress. |
| **Tests stay mock-based** | SQL builders are pure functions asserted on compiled SQL + params; the ADBC writer is tested against a mocked driver. No DB needed in CI. (A real-PostGIS layer was considered and deferred.) |

## Files

```
arrow_reader.py     NEW  streaming Arrow sources (OGR / Parquet / db→db) + SRID/encoding helpers
postgis_writer.py   NEW  ADBC bulk load + geometry fixup DDL + URI/​schema normalisation
transform_sql.py    rewritten  one SELECT builder + process/preview/SRID executors
filter_sql.py        +  build_filter_clause extracted for reuse
ingestion.py        rewritten  thin per-source orchestrators (CSV/COPY plumbing deleted)
transform{,_columns,_geom_point,_projection,_encoding}.py   DELETED  in-memory pandas stack
```

## Comparison with `origin/use-gdal` (the ogr2ogr approach)

Both branches share the **same transformation idea** (one SQL SELECT → CTAS for
process, `ST_AsText`/`ST_AsGeoJSON` for preview). They diverge entirely on
**ingestion** and on the **runtime/packaging** that implies.

| Aspect | This branch (pyogrio + ADBC) | `use-gdal` (ogr2ogr) |
|---|---|---|
| **Reads** | `pyogrio.open_arrow` / pyarrow / server-side cursor, streamed | `ogr2ogr` subprocess reads the source directly |
| **Writes** | `adbc_ingest` COPY BINARY, in-process | `ogr2ogr -f PostgreSQL`, subprocess |
| **GDAL delivery** | pip wheels (`pyogrio`) — no system GDAL | conda-forge GDAL ≥3.12 via **micromamba**, in a **vendored ~2300-line Airflow base Dockerfile** (bookworm ships only GDAL 3.6, no Parquet driver) |
| **Install footprint** | a few wheels in the existing image | new base image + `LD_LIBRARY_PATH` wrapper scripts; entangled with a Python 3.13 / Airflow 3.2.2 bump |
| **Credentials** | never leave the process | DB password in `PG:` connection string and `GDAL_HTTP_USERPWD` → visible in `argv` / `/proc/<pid>/cmdline` |
| **Download / upload memory** | streamed to disk with finite timeouts | still buffers `response.content`; upload path untouched |
| **Cast semantics** | inline CASE in the SELECT | plpgsql `CREATE FUNCTION` helpers, per-row `EXCEPTION` subtransactions (DDL on `public`, slow at scale) |
| **Memory** | bounded by batch size, end to end | bounded by ogr2ogr internals (also streaming) |
| **Maintenance** | pure Python, pip-managed; more *our* code to own (readers/writer) | less code (delegates to GDAL), but a heavy bespoke image to maintain; branch was ~89 commits behind main |
| **Robustness of edge formats** | depends on pyogrio/GDAL coverage (same engine) + our normalisation | battle-tested GDAL CLI handles encodings/quirks directly |

### Why this branch was chosen

The decisive factor was **packaging**: keeping the stack pip-only avoids a large,
permanent maintenance burden (the vendored Airflow image + conda GDAL +
library-path shims) that exists *only* because PyPI GDAL is source-only and
Debian's GDAL is too old for Parquet. We accept owning a bit more code (the
Arrow readers and the ADBC writer) in exchange for no system-level GDAL, no
credentials in process argv, in-process error handling, and streaming on both
the download and upload sides too.

### What `use-gdal` does better (worth borrowing)

- ogr2ogr delegates encoding detection, format quirks and driver selection to
  GDAL — less of *our* code to keep correct for exotic inputs.
- It already carries the OGC Basic-Auth credential decryption path
  (`encrypted_credentials` → `GDAL_HTTP_USERPWD`) that this branch should reach
  parity on for protected WFS/OAPIF services.

## Follow-ups / not done here

- **Docker smoke test** (live stack): ingest GeoJSON / latin-1 shapefile / CSV /
  db→db, then exercise filter + rename + cast + force_projection through the
  preview endpoint and the process DAG; confirm the final table row count
  reflects the WHERE filter, and has the `id_datafeeder` PK + GIST index.
- **Pre-existing test failures** unrelated to this work (fail on HEAD too):
  libs `test_database` (4), `test_geoserver` (7), `test_utils` sanitize_name (2);
  backend `tests/services/test_files.py` (4).
- Protected OGC service auth (mirror `use-gdal`'s credential decryption).

## Pandas removed from the ELT runtime

The DAG generator's `get_pandas_df(...).to_dict()` is replaced by a raw-cursor
`get_records_as_dicts` helper, and `normalize_nan` drops `pd.isna` for a plain
None/NaN check. pandas is no longer a runtime dependency of `apps/elt`, and
geopandas was already runtime-free. Both remain available **only as dev
dependencies** (via the `data_manipulation` workspace member) for test fixtures;
neither is installed into the runtime image (`uv sync --no-dev`).
