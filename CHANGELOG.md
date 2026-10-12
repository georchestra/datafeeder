# Changelog

## [2.1.0] 

Changes since [2.0.1].

### Highlights

- **GDAL/ogr2ogr ingestion replaces geopandas** (#46): geospatial files are now loaded into PostGIS
  with `ogr2ogr`, and transformations run as SQL in PostGIS. The Airflow image is now built on a
  Debian Trixie + GDAL base image, and Python is bumped to 3.13.
- **Local task executor** (#93): `TASK_EXECUTOR=LOCAL` runs staging and processing inside the
  backend process, without Airflow. Scheduled/recurring re-ingestion is not supported in this mode.
- **Admin tools for datasets** (#168): administrators can export a dataset definition, import it on
  another platform, reassign it to another owner and/or organization (moving the table and layer
  accordingly), delete it while keeping its layer and metadata, and read staging logs.

### Added

- Dashboard filters for organization and owner (#144, #147), and for public access and recurrence
  (#145).
- `joinable-tables` and `joinable-columns` endpoints (#117).
- GeoNetwork templates chosen per group, based on the template's owner group (#120).
- Metadata online resources are added to the record once the dataset is published, and updated when
  the dataset title changes. The `mrd:MD_Distribution` section is created if missing.
- New setting `METADATA_ADMIN_DEFAULT_GROUP_NAME`: GeoNetwork group used when the metadata owner is
  an administrator.
- URL imports fall back to a GET request when the server rejects HEAD (#92).
- Shapefile encoding is read from a `.cst` sidecar file when present (#169).
- A second sample source database with tables and views for local development (#156).
- End-to-end test suite (#89) and a CI workflow running the Python and `data_manipulation` tests.
- Documentation: Kubernetes deployment, databases and their interactions, egress, local executor,
  and a documentation template (#121, #149).

### Changed

- Airflow bumped to 3.3.2, along with its Python client (#155). DAGs now set run limits and use
  deferrable tasks (#186).
- Airflow DAG callbacks go through an internal-only gateway path; `/internal` routes are excluded
  from the OpenAPI schema (#123).
- The dataset title is no longer pre-filled in the import wizard; the field gets autofocus instead
  (#142).
- i18n: topics now use ISO keys (instead of INSPIRE) aligned with the GN-UI codelist, contact role
  translations match GeoNetwork, and new association markers were added (#162).
- Node bumped to 24, Angular to the latest 20.3 patches (#179), geonetwork-ui to 2.10.2 (#135).
- The PostGIS image version is updated in Docker Compose.

### Fixed

- Fixed a crash at startup when a PostgreSQL password contains `$`. Passwords are now URL-encoded
  in the connection URIs (#116).
- Fixed GeoServer publishing for prefilled integrity links, which have no final table name (#92).
- Fixed a deadlock in the local executor on self-referential callbacks (#143).
- Shapefiles with an invalid text encoding are caught instead of failing the import (#107);
  encoding detection works again for shapefiles without a `.cpg` file.
- Ingestion:
  - ZIP archives created with the macOS Finder are accepted.
  - ZIP files are opened through GDAL's `/vsizip/`.
  - Values in the GDAL `PG:` connection string are quoted.
  - `ogr2ogr` errors are reported instead of being hidden.
  - EPSG:4326 is only forced for OGC API - Features sources.
- The spatial index is recreated after `CREATE TABLE AS` in transformations.
- The `ogr2ogr` command, which includes credentials, is no longer logged.
- HTTP downloads are streamed to disk instead of being held in memory.

### Removed

- The geopandas stack and the `chardet` dependency (#115, #154).

### Dependencies

- Many dependency updates in the backend, ELT, frontend and e2e tests, including cryptography 50,
  pyjwt 2.15, urllib3 2.8, anyio 4.14, werkzeug 3.1.9, tornado 6.5.9 and mkdocs-material 9.7.

[2.1.0]: https://github.com/georchestra/datafeeder/compare/2.0.1...2.1.0
[2.0.1]: https://github.com/georchestra/datafeeder/releases/tag/2.0.1
