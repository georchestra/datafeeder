# GSMEL-788 — Ingestion Tunnel: Service & API OGC

## Context

Users need to ingest data from WFS or OGC API Features services. Unlike a static URL, these sources require both a service URL and a layer name. The GeoNetwork-UI `OnlineServiceResourceInputComponent` (with `featuresOnly=true`) handles URL entry + layer discovery/selection. The feature must support recurrence (scheduled refresh) and pre-populate the title (Step 2) with the layer name.

geonetwork-ui is installed locally at `apps/frontend/node_modules/geonetwork-ui`. The component `gn-ui-online-service-resource-input` already has a `featuresOnly` input that limits the protocol picker to WFS + OGC API Features.

---

## Critical Files

| File | Role |
|------|------|
| `apps/backend/src/models/integrity_link.py` | Add `source_layer` field |
| `apps/backend/src/models/data_import.py` | Expose `source_layer` in responses; update `StagingMetadataResponse` |
| `apps/backend/src/api/routes/ingestion/staging.py` | Implement `ImportType.API` case; add form params |
| `apps/backend/src/core/task_executor.py` | Add `source_layer` to abstract `trigger_staging_task` |
| `apps/backend/src/services/executors/airflow_executor.py` | Pass `source_layer` to DAG conf |
| `apps/elt/dags/staging_dag.py` | Add `source_layer` Param |
| `apps/elt/dags/task_groups/ingestion.py` | Add `api_ingest_step`; update branching |
| `apps/elt/dags/process_dag.py` | Add `source_layer` Param; update enum |
| `apps/elt/dags/process-dag-generator.py` | Select + pass `source_layer` |
| `libs/data_manipulation/src/data_manipulation/ingestion.py` | Add `ingest_data_from_wfs_into_postgis` |
| `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.ts` | Add `'api'` source type + geonetwork-ui component |
| `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.html` | Radio button + service input section |
| `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts` | validSource, createImportRequest, initialApiSource, title from layer |
| `apps/frontend/src/app/core/api/` | Regenerate TS client after backend changes |
| `apps/frontend/src/assets/i18n/en.json` + `fr.json` | New translation keys |

---

## Implementation Steps

### 1. Backend: Add `source_layer` to `IntegrityLink`

In `apps/backend/src/models/integrity_link.py`, add:
```python
source_layer: Optional[str] = Field(default=None, max_length=256)
```

Create an Alembic migration adding the column `source_layer VARCHAR(256)` to `datafeeder.integrity_link`.

### 2. Backend: Expose `source_layer` in response models

In `apps/backend/src/models/data_import.py`:
- Add `source_layer: str | None` to `IntegrityLinkResponse` and `IntegrityLinkListItem`
- In `StagingMetadataResponse`, add `layer_name: str | None = None` (the backend will populate this from `IntegrityLink.source_layer` when `import_type == API`, so the frontend can use it as the initial title)

### 3. Backend: Implement `ImportType.API` in staging

In `apps/backend/src/api/routes/ingestion/staging.py`:

**Add form parameters** to both `submit_staging` and `edit_staging`:
```python
service_url: Optional[str] = Form(None),
layer_name: Optional[str] = Form(None),
```

**Add to `_process_import_source` signature and body:**
```python
service_url: Optional[str] = None,
layer_name: Optional[str] = None,
```
```python
case ImportType.API:
    if not service_url or not layer_name:
        raise HTTPException(status_code=400, detail="Service URL and layer name are required for API import type")
    source = service_url.strip()
    url = source
    # source_file_name = layer_name (used as title hint)
    source_file_name = layer_name.strip()
    # auth_enabled = False for now (OGC public services)
```

**Set `integrity_link.source_layer`** when creating/updating the IntegrityLink record.

**Pass `source_layer` to `_trigger_staging_task`** (add param, thread through to executor).

### 4. Backend: Task executor and Airflow executor

In `apps/backend/src/core/task_executor.py`, add `source_layer: str | None = None` to `trigger_staging_task` abstract method.

In `apps/backend/src/services/executors/airflow_executor.py`, add `source_layer` to `conf` dict passed to staging DAG.

### 5. Backend: Staging metadata endpoint

In the `get_staging_metadata` endpoint (in `staging.py`), when building `StagingMetadataResponse`, if `import_type == API` and `integrity_link.source_layer` is set, populate `layer_name = integrity_link.source_layer`. The frontend will read `layer_name` as the initial title.

### 6. ELT: staging_dag.py

Add `source_layer` Param:
```python
"source_layer": Param(
    default=None,
    type=["null", "string"],
    description="Layer/feature name for API/WFS import",
),
```

### 7. ELT: task_groups/ingestion.py

Update branching to route `"API"` → `api_ingest_step`.

Add `api_ingest_step`:
```python
@task(task_id="api_ingest_step")
def api_ingest_step(**context):
    params = context.get("params", {})
    target_table_name = params.get("staging_table_name")
    source = params.get("source", "")
    source_layer = params.get("source_layer", "")
    ...
    ingest_data_from_wfs_into_postgis(source, source_layer, target_table_name, engine, schema)
```

Wire it: `do_branching() >> [..., api_ingest_step()]`

### 8. ELT: process_dag.py

Add `source_layer` Param (type `["null", "string"]`).  
Update `source_type` enum to include `"API"` (or keep "OGC_WFS" and map from it — align with `ImportType.API.value.upper() == "API"`).

Pass `source_layer` through to the ingestion group via XCom or params.

### 9. ELT: process-dag-generator.py

Update SQL to also select `source_layer`:
```sql
SELECT ..., source_layer, ...
FROM datafeeder.integrity_link
WHERE schedule NOTNULL AND schedule NOT LIKE ''
```

Add `"source_layer": config.get("source_layer")` to the `conf` dict of `TriggerDagRunOperator`.

### 10. data_manipulation: WFS ingestion

In `libs/data_manipulation/src/data_manipulation/ingestion.py`, add:
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

Also export it in `data_manipulation/__init__.py`.

### 11. Frontend: data-source-selector

In `data-source-selector.component.ts`:
- Add `'api'` to `SourceType` and `RadioType`
- Add to `SourceData`: `serviceUrl?: string`, `layerName?: string`, `serviceProtocol?: string`
- Add form controls: `serviceUrl`, `layerName`, `serviceProtocol`
- Import `OnlineServiceResourceInputComponent` from geonetwork-ui and add to `imports`
- Add `initialApiSource = input<{ url: string; layerName: string; protocol: string } | null>(null)` and an effect to pre-populate the form (like `initialDatabaseSource`)
- Handle radio change for `'api'` type
- Handle `serviceChange` event from the geonetwork-ui component: extract `url.toString()`, `identifierInService`, `accessServiceProtocol` and patch the form

In `data-source-selector.component.html`:
- Add `<mat-radio-button value="api">` for "Service & API OGC"
- Add a conditional section `@if (radio === 'api')` containing:
  ```html
  <gn-ui-online-service-resource-input
    [featuresOnly]="true"
    [service]="currentService"
    (serviceChange)="handleServiceChange($event)"
  />
  ```
- The geonetwork-ui component handles its own internal state; we react to its `serviceChange` output

### 12. Frontend: data-import-wizard

In `data-import-wizard.component.ts`:
- Add API case to `validSource`:
  ```ts
  (source.type === 'api' && !!source.serviceUrl && !!source.layerName)
  ```
- Add API case to `createImportRequest()`:
  ```ts
  body = { type: 'api', service_url: source.serviceUrl, layer_name: source.layerName }
  ```
- Add `initialApiSource` computed signal (similar to `initialDatabaseSource`):
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
- For title pre-population: after `refreshMetadata()`, if `metadata.layer_name` is set and no existing title, set `metadata.title = metadata.layer_name`

### 13. Frontend: i18n keys

Add to both `en.json` and `fr.json`:
```json
"import.dataSource.chooseType.api": "Service & API OGC",
```

### 14. Regenerate TypeScript API client

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
