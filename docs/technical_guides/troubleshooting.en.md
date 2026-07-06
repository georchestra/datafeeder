# Troubleshooting

Datafeeder is a chain of loosely-coupled components (backend, Airflow, GeoServer, GeoNetwork). When troubleshooting,
check each link in the chain in turn, following the [dataset lifecycle](presentation.md#dataset-lifecycle).

## A dataset is stuck "staging" or "processing"

- Check the corresponding DAG run in the Airflow UI (`staging_dag` or `process_dag`) for the dataset's run id.
- If the DAG run failed, its logs will point to the actual cause (unreachable source, bad credentials, invalid
  data, projection error, etc.).
- If the DAG run **succeeded** but the dataset still looks stuck in the UI, the issue is likely on the callback
  path: check that the backend is reachable at the URL Airflow was given (`BACKEND_INTERNAL_URL`), and check the
  backend logs for the corresponding `success_callback_url` / `failure_callback_url` call.

## Staging or processing fails and leaves nothing behind

This is expected: a failed `staging_dag` run deletes the `IntegrityLink` and the staging table; a failed
`process_dag` run drops the partial final table. Datasets are designed to never sit in a half-published state.
Fix the underlying cause (see the DAG logs) and re-submit the import.

## The published layer/metadata doesn't reflect the latest data

- If the dataset has a recurring schedule, check the schedule actually ran: dataset dashboard should show a
  "last run" for it, and the corresponding `process_dag` run should show as successful in Airflow.
- If the recurring re-run failed, the previously published layer and metadata are left untouched — check the DAG
  run's logs for why the re-fetch/transform failed.

## GeoServer or GeoNetwork publication fails

- Verify `GEOSERVER_INTERNAL_URL` / `GEOSERVER_USER` / `GEOSERVER_PASSWORD` (resp. the `GEONETWORK_*` settings) in
  the [backend configuration](configuration/backend.md) point to a reachable instance with valid credentials.

## Database source import fails

- `SOURCE_DATABASES` must contain a valid SQLAlchemy URI for the source key selected in the wizard. A malformed or
  unreachable URI will surface as a staging failure — check the `staging_dag` run's logs.

## Frontend shows unexpected/outdated fields

The frontend's API client is generated from the backend's OpenAPI schema. If you (or a colleague) changed backend
routes/models without regenerating it, the two will drift apart. See
[Regenerating the API client](configuration/frontend.md#regenerating-the-api-client).
