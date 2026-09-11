# Databases

Datafeeder spans **three** logically separate PostgreSQL databases. They can be collapsed onto fewer physical
instances (see [below](#can-they-be-merged)), but keep the distinction in mind: it explains several settings
(`POSTGRES_DATAFEEDER_*` vs `POSTGRES_DATA_*`, the Airflow `metadataConnection`) and a few deployment gotchas.

| Database | Holds | Written/read by |
|---|---|---|
| **geOrchestra DB** (`datafeeder` schema) | Datafeeder's own bookkeeping: `IntegrityLink` records, authorization rules, schedules | Backend (read/write), Airflow (read-only, to find datasets scheduled for a recurring re-run) |
| **Data DB** (`data` / `staging` schemas) | The actual dataset content: staging tables during ingestion, then the final published tables | Backend, Airflow DAGs, GeoServer (via JNDI, to serve the published layers) |
| **Airflow metadata DB** | Airflow's own internal schema: DAG/task run history, logs metadata, encrypted Connections | Airflow only |

## Why not just one database?

- **The geOrchestra DB** follows the platform's existing convention: one shared database, one schema per module
  (console, etc.). Datafeeder's own schema is small and low-churn — it just tracks *which* datasets exist and
  their rules, not their content.
- **The data DB** is isolated because it has a completely different profile: it can grow arbitrarily large (one
  table per published dataset), and — unlike every other piece of geOrchestra state — **GeoServer reads from it
  directly** (via JNDI), not through an API. Keeping it separate lets you size, back up, and scale it
  independently of platform metadata, and means GeoServer only ever needs credentials scoped to dataset content,
  never to the rest of the platform (users, orgs, LDAP-adjacent tables, etc.).
- **The Airflow metadata DB** is owned end-to-end by Airflow itself: its schema is created and migrated by Airflow's
  own release cycle, independent of Datafeeder/geOrchestra upgrades. It also churns heavily (a row per task
  instance/log — see the `airflowDbCleanup` CronJob in the Helm chart, which periodically purges old rows) and
  stores encrypted credentials (Airflow Connections, encrypted with the Fernet key). Keeping it separate avoids
  coupling its lifecycle/retention policy to the rest of the platform, and limits the blast radius of those stored
  credentials.

## Can they be merged?

- **geOrchestra DB + Data DB**: yes, safely — point `POSTGRES_DATA_*` at the same instance as
  `POSTGRES_DATAFEEDER_*` (this is the default if `POSTGRES_DATA_*` is left unset, see
  [backend configuration](backend.md)). You lose the sizing/least-privilege isolation described above, which is
  fine for smaller deployments.
- **Airflow metadata DB**: you *can* point it at the same PostgreSQL instance, but give it its own logical
  database (not a schema of one of the two above) — Airflow expects exclusive ownership of its database and
  manages its own migrations there.

## Schemas and extensions to create

Alembic (the backend's migration tool) does **not** bootstrap the schema from scratch: its baseline migration is a
no-op, it only applies changes on top of an already-existing schema (see
[`001_baseline.py`](https://github.com/georchestra/datafeeder/blob/main/apps/backend/alembic/versions/001_baseline.py)).
The Docker Compose setup runs the init scripts below automatically before the backend starts; any other deployment
(Kubernetes included) must run them once, manually, against the target instance(s) before the first install:

| Target | Script | Creates |
|---|---|---|
| geOrchestra DB | [`docker/datafeeder-init.sql`](https://github.com/georchestra/datafeeder/blob/main/docker/datafeeder-init.sql) (same content as [`georchestra/migrations/26.0/db_migration_new_datafeeder.sql`](https://github.com/georchestra/georchestra/blob/master/migrations/26.0/db_migration_new_datafeeder.sql), for platforms upgrading from 25 to 26) | `datafeeder` schema, `pgcrypto` extension, `staging` schema/grants |
| Data DB | [`docker/data-db-init.sql`](https://github.com/georchestra/datafeeder/blob/main/docker/data-db-init.sql) | `postgis` extension, `data`/`staging` schemas |
| Airflow metadata DB (only if externally managed, i.e. `airflow.postgresql.enabled: false` on the Helm chart) | [`docker/datadir/database/140-airflow.sql`](https://github.com/georchestra/datafeeder/blob/main/docker/datadir/database/140-airflow.sql) | `airflow` schema |

Once these exist, `alembic upgrade head` runs automatically on every backend start and takes care of subsequent
schema changes — no further manual SQL is needed.

For the Helm-chart-specific secret wiring (which secret feeds which database, and a chart gap to watch out for),
see [Kubernetes installation](../installation/kubernetes.md#1-databases).
