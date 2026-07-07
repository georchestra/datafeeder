# Managing datasets

The dataset dashboard lists every `IntegrityLink` known to the platform: one row per dataset.

From this dashboard you can:

- open a dataset to review or edit its transformation and re-publish it
- re-run the staging step against the original source (**re-staging**)
- follow the underlying Airflow task's progress and logs while a staging or processing run is in progress
- delete a dataset

## Recurring refresh

A dataset can be scheduled to re-import itself automatically. Available presets:

- Every minute *(mainly for testing)*
- Every hour
- Every day
- Every week
- Every month
- Every year

On each run, Datafeeder re-fetches the data from the dataset's original source and re-applies its transformation, so
the published layer and metadata stay in sync with the source without manual intervention.

## Deleting a dataset

Deleting a dataset is a full cleanup, not a soft delete. It:

- unpublishes the GeoServer layer
- deletes the GeoNetwork metadata record
- drops the staging and final PostgreSQL tables
- removes the `IntegrityLink` record and its schedule, if any

There is no undo: reimporting the same source afterwards creates a brand new dataset.
