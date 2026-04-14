# GSMEL-788 — Ingestion Tunnel: Service & API OGC

## Context

Users need to ingest data from WFS or OGC API Features services. Unlike a static URL, these sources require both a service URL and a layer name. The GeoNetwork-UI `OnlineServiceResourceInputComponent` (with `featuresOnly=true`) handles URL entry + layer discovery/selection. The feature must support recurrence (scheduled refresh) and pre-populate the title (Step 2) with the layer name.

`geonetwork-ui` is installed locally at `apps/frontend/node_modules/geonetwork-ui`. The component `gn-ui-online-service-resource-input` is exported from `'geonetwork-ui'` (confirmed in `index.d.ts`) and accepts a `[service]: DatasetServiceDistribution` input (also from `'geonetwork-ui'`) and emits `(serviceChange): DatasetServiceDistribution`.

---

## Current State

- `ImportType.API = "api"` already exists in `apps/backend/src/models/data_import.py:25`
- `staging_dag.py` already includes `"API"` in the `source_type` enum
- `staging.py` has a stub for `ImportType.API` that raises HTTP 501 (line 207)
- `process_dag.py` uses `"OGC_WFS"` in its enum (must be changed to `"API"`)
- No `source_layer` field anywhere in the backend or ELT yet
- Frontend `SourceType` does not include `'api'`
- No SQL column for `source_layer` yet (schema is managed via `docker/datadir/database/130-datafeeder.sql`, no Alembic)

---

## Critical Files

| File | Role |
|------|------|
| `docker/datadir/database/130-datafeeder.sql` | Add `source_layer` column to DDL |
| `apps/backend/src/models/integrity_link.py` | Add `source_layer` field |
| `apps/backend/src/models/data_import.py` | Add `source_layer` to response models; add `layer_name` to `StagingMetadataResponse` |
| `apps/backend/src/api/routes/ingestion/staging.py` | Implement `ImportType.API` case; add form params; set `source_layer` on IntegrityLink |
| `apps/backend/src/core/task_executor.py` | Add `source_layer` to abstract `trigger_staging_task` |
| `apps/backend/src/services/executors/airflow_executor.py` | Pass `source_layer` to DAG conf |
| `apps/elt/dags/staging_dag.py` | Add `source_layer` Param |
| `apps/elt/dags/task_groups/ingestion.py` | Add `api_ingest_step`; update branching |
| `apps/elt/dags/process_dag.py` | Fix enum: replace `"OGC_WFS"` with `"API"`; add `source_layer` Param |
| `apps/elt/dags/process-dag-generator.py` | Select + pass `source_layer` in SQL + conf |
| `libs/data_manipulation/src/data_manipulation/ingestion.py` | Add `ingest_data_from_wfs_into_postgis` |
| `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.ts` | Add `'api'` source type + geonetwork-ui component |
| `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.html` | Radio button + service input section |
| `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts` | validSource, createImportRequest, initialApiSource, title from layer |
| `apps/frontend/src/assets/i18n/en.json` + `fr.json` | New translation keys |

---

## Implementation Steps

### 1. SQL schema + IntegrityLink model

**`docker/datadir/database/130-datafeeder.sql`** — add after `source_file_type`:
```sql
source_layer varchar(256) NULL,
```

**`apps/backend/src/models/integrity_link.py`** — add after `source_file_type`:
```python
source_layer: Optional[str] = Field(default=None, max_length=256)
```

> For existing dev DBs, run: `ALTER TABLE datafeeder.integrity_link ADD COLUMN source_layer VARCHAR(256);`

### 2. Response models

**`apps/backend/src/models/data_import.py`**:

- Add `source_layer: str | None = None` to `IntegrityLinkListItem` (after `source_url`)
- Add `source_layer: str | None = None` to `IntegrityLinkResponse` (after `source_url`)
- Add `layer_name: str | None = None` to `StagingMetadataResponse` (the frontend reads this to pre-populate the title)

### 3. Staging endpoint — implement API case

**`apps/backend/src/api/routes/ingestion/staging.py`**:

**Add to `_ImportSourceResult.__init__`**:
```python
source_layer: str | None = None
self.source_layer = source_layer
```

**Add to `_process_import_source` signature**:
```python
service_url: Optional[str] = None,
layer_name: Optional[str] = None,
```

**Replace the `ImportType.API` stub**:
```python
case ImportType.API:
    if not service_url or not layer_name:
        raise HTTPException(
            status_code=400,
            detail="Service URL and layer name are required for API import type",
        )
    source = service_url.strip()
    url = source
    source_file_name = layer_name.strip()
    auth_enabled = False
    return _ImportSourceResult(
        source=source, url=url,
        source_file_name=source_file_name,
        source_file_type=None,
        auth_enabled=auth_enabled,
        source_layer=layer_name.strip(),
    )
```

**Add form params** to both `submit_staging` and `edit_staging`:
```python
service_url: Optional[str] = Form(None),
layer_name: Optional[str] = Form(None),
```

**Thread through** in both calls to `_process_import_source`:
```python
service_url=service_url,
layer_name=layer_name,
```

**In `submit_staging`**, when creating `IntegrityLink`, add:
```python
source_layer=import_source.source_layer,
```

**In `edit_staging`**, after calling `_process_import_source`, update the integrity link:
```python
integrity_link.source_layer = import_source.source_layer
```

**In `get_staging_metadata`** (line ~758), update the title logic to include API type:
```python
if not title and integrity_link.source_import_type == ImportType.API and integrity_link.source_layer:
    title = integrity_link.source_layer
```

And in `StagingMetadataResponse(...)` construction, add:
```python
layer_name=integrity_link.source_layer if integrity_link.source_import_type == ImportType.API else None,
```

### 4. Task executor + Airflow executor

**`apps/backend/src/core/task_executor.py`** — add to `trigger_staging_task` abstract signature:
```python
source_layer: str | None = None,
```

**`apps/backend/src/services/executors/airflow_executor.py`** — add to `conf` dict:
```python
"source_layer": source_layer,
```
And add `source_layer: str | None = None` to the method signature.

**`apps/backend/src/api/routes/ingestion/staging.py`** — in `_trigger_staging_task`, add `source_layer` param and thread it through to `executor.trigger_staging_task(source_layer=...)`.

### 5. ELT: staging_dag.py

**`apps/elt/dags/staging_dag.py`** — add `source_layer` Param alongside the existing params:
```python
"source_layer": Param(
    default=None,
    type=["null", "string"],
    description="Layer/feature name for API/WFS import",
),
```

### 6. ELT: task_groups/ingestion.py

**Update `do_branching`** — add `"API"` case:
```python
case "API":
    return f"{group_id}.api_ingest_step"
```

**Add `api_ingest_step` task** (modeled after `database_ingest_step`):
```python
@task(task_id="api_ingest_step")
def api_ingest_step(**context: dict[str, Any]) -> None:
    params = context.get("params", {})
    ti = context.get("ti")

    target_table_name = params.get("staging_table_name")
    if not target_table_name and ti:
        target_table_name = ti.xcom_pull(task_ids="generate_staging_table_name")
    if not target_table_name:
        raise AirflowException("staging_table_name is not provided")

    source = params.get("source", "")
    source_layer = params.get("source_layer", "")
    if not source_layer:
        raise AirflowException("source_layer is required for API import")

    engine = get_data_sql_engine()
    ingest_data_from_wfs_into_postgis(source, source_layer, target_table_name, engine, schema=get_staging_schema())
```

Add `ingest_data_from_wfs_into_postgis` to the import from `data_manipulation`.

**Wire into the task group** alongside the other step tasks.

### 7. ELT: process_dag.py

- Replace `"OGC_WFS"` with `"API"` in the `source_type` enum (line ~61)
- Add `source_layer` Param:
```python
"source_layer": Param(
    default=None,
    type=["null", "string"],
    description="Layer/feature name for API/WFS import",
),
```

### 8. ELT: process-dag-generator.py

**Update SQL** to select `source_layer`:
```sql
SELECT 
    ...,
    source_layer,
    ...
FROM datafeeder.integrity_link
WHERE schedule NOTNULL AND schedule NOT LIKE ''
```

**Update `conf`** in `TriggerDagRunOperator`:
```python
"source_layer": config.get("source_layer"),
```

### 9. data_manipulation: WFS ingestion

**`libs/data_manipulation/src/data_manipulation/ingestion.py`** — add:
```python
def ingest_data_from_wfs_into_postgis(
    service_url: str,
    layer_name: str,
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
) -> None:
    """Ingest a WFS or OGC API Features layer into PostGIS using GeoPandas/GDAL."""
    logger.info(f"Ingesting WFS layer '{layer_name}' from {service_url} into {table_name}")
    try:
        gdf = gpd.read_file(f"WFS:{service_url}", layer=layer_name)
        write_data_to_postgis(gdf, table_name, engine, schema)
    except Exception as e:
        logger.error(f"Error ingesting WFS layer {layer_name} from {service_url}: {e}")
        raise
```

Also export it in `libs/data_manipulation/src/data_manipulation/__init__.py`.

### 10. Frontend: data-source-selector

**`data-source-selector.component.ts`**:

- Change `SourceType` to: `'url' | 'file' | 'ftp' | 'database' | 'api'`
- Change `RadioType` to: `'file' | 'ftp' | 'database' | 'api'`
- Add to `SourceData`: `serviceUrl?: string`, `layerName?: string`, `serviceProtocol?: string`
- Add form controls: `serviceUrl: fb.control<string | null>(null)`, `layerName: fb.control<string | null>(null)`, `serviceProtocol: fb.control<string | null>(null)`
- Import `OnlineServiceResourceInputComponent, DatasetServiceDistribution` from `'geonetwork-ui'` and add to component `imports`
- Add `initialApiSource = input<{ url: string; layerName: string; protocol: string } | null>(null)` and an `effect` to pre-populate the form (similar to `initialDatabaseSource`)
- Add `currentService` signal: `signal<DatasetServiceDistribution>({ type: 'service', url: null, accessServiceProtocol: 'wfs' })`
- Add `handleServiceChange(service: DatasetServiceDistribution)` method that patches: `serviceUrl: service.url?.toString()`, `layerName: service.identifierInService ?? service.name`, `serviceProtocol: service.accessServiceProtocol`
- Add `marker('import.dataSource.chooseType.api')` call
- Update `resetSource()` to also null out `serviceUrl`, `layerName`, `serviceProtocol`
- Update `valueChanges` subscription to emit `serviceUrl`, `layerName`, `serviceProtocol`

**`data-source-selector.component.html`**:
- Add `<mat-radio-button value="api">{{ 'import.dataSource.chooseType.api' | translate }}</mat-radio-button>`
- Add conditional section `@if (radio === 'api')`:
```html
<gn-ui-online-service-resource-input
  [featuresOnly]="true"
  [service]="currentService()"
  (serviceChange)="handleServiceChange($event)"
/>
```

### 11. Frontend: data-import-wizard

**`data-import-wizard.component.ts`**:

- Add API case to `validSource`:
  ```ts
  (source.type === 'api' && !!source.serviceUrl && !!source.layerName)
  ```
- Add API case to `createImportRequest()`:
  ```ts
  } else if (source.type === 'api') {
    body = { type: 'api', service_url: source.serviceUrl, layer_name: source.layerName }
  }
  ```
- Add `initialApiSource = computed(...)`:
  ```ts
  initialApiSource = computed(() => {
    const link = this.integrityLinkStore.integrityLink()
    if (link?.source_import_type === 'api' && link.source_url && link.source_layer) {
      return { url: link.source_url, layerName: link.source_layer, protocol: 'wfs' }
    }
    return null
  })
  ```
- Pass `[initialApiSource]="initialApiSource()"` to `app-data-source-selector`
- After `refreshMetadata()` sets `metadata`, if `metadata.layer_name` is set and no existing `integrity_title`, use it as initial title hint (the `title` field in `StagingMetadataResponse` already handles this via the backend)

### 12. Frontend: i18n keys

Add to both `apps/frontend/src/assets/i18n/en.json` and `fr.json`:
```json
"import.dataSource.chooseType.api": "Service & API OGC"
```
(French: `"Service & API OGC"` — same)

### 13. Regenerate TypeScript API client

After backend OpenAPI contract stabilizes:
```sh
cd apps/frontend && npm run generate-api
```

---

## API contract changes (summary)

**Staging POST/PUT** — two new optional form fields: `service_url`, `layer_name`.

**`IntegrityLinkResponse` / `IntegrityLinkListItem`** — new field `source_layer: string | null`.

**`StagingMetadataResponse`** — new field `layer_name: string | null`.

---

## Verification

1. `make up-light` → navigate to import wizard
2. Select "Service & API OGC" radio button — verify geonetwork-ui component appears
3. Enter a public WFS endpoint URL; click refresh → layer list appears; select a layer
4. Click "Configure Dataset" → DAG runs successfully; Step 2 shows layer name as title
5. Adjust title/columns, validate → dataset is processed
6. Return to import and edit the source → WFS URL and layer are pre-populated
7. Set a recurrence schedule and validate → scheduled DAG picks up `source_layer` and refreshes
8. Run `make check-all-python` and `cd apps/frontend && npm run lint && npm run test:ut`
