# Databases

Datafeeder uses **three** logically separate PostgreSQL databases:

| Database | Holds | Used by |
|---|---|---|
| **geOrchestra DB** (`datafeeder` schema) | `IntegrityLink` records, authorization rules, schedules | Backend (read/write), Airflow (read, to find scheduled re-runs) |
| **Data DB** (`data` / `staging` schemas) | Dataset content: staging tables, then published tables | Backend, Airflow DAGs, GeoServer (via JNDI) |
| **Airflow metadata DB** | DAG/task run history, encrypted Connections | Airflow only |

## Why separate them?

- **geOrchestra DB**: follows the platform convention of one shared database with one schema per module.
- **Data DB**: can grow arbitrarily large and is read **directly by GeoServer**. Keeping it apart lets you size and
  back it up independently, and GeoServer only gets credentials scoped to dataset content.
- **Airflow metadata DB**: schema owned and migrated by Airflow, high churn (purged by the `airflowDbCleanup`
  CronJob), and stores Fernet-encrypted credentials.

## Can they be merged?

- **geOrchestra DB + Data DB**: yes — leave `POSTGRES_DATA_*` unset and it defaults to `POSTGRES_DATAFEEDER_*`
  (see [backend configuration](backend.md)). Fine for smaller deployments.
- **Airflow metadata DB**: can share the PostgreSQL instance, but needs its own logical database, since Airflow
  manages its own migrations there.

## Initialization scripts

Alembic does **not** bootstrap the schema: its [baseline migration](https://github.com/georchestra/datafeeder/blob/main/apps/backend/alembic/versions/001_baseline.py)
is a no-op. Docker Compose runs the scripts below automatically; any other deployment (Kubernetes included) must run
them once before the first install:

| Target | Script | Creates |
|---|---|---|
| geOrchestra DB | [`docker/datafeeder-init.sql`](https://github.com/georchestra/datafeeder/blob/main/docker/datafeeder-init.sql) (same as [`migrations/26.0/db_migration_new_datafeeder.sql`](https://github.com/georchestra/georchestra/blob/master/migrations/26.0/db_migration_new_datafeeder.sql) when upgrading from 25) | `datafeeder` schema, `pgcrypto`, `staging` schema/grants |
| Data DB | [`docker/data-db-init.sql`](https://github.com/georchestra/datafeeder/blob/main/docker/data-db-init.sql) | `postgis`, `data`/`staging` schemas |
| Airflow metadata DB (only if `airflow.postgresql.enabled: false`) | [`docker/datadir/database/140-airflow.sql`](https://github.com/georchestra/datafeeder/blob/main/docker/datadir/database/140-airflow.sql) | `airflow` schema |

After that, `alembic upgrade head` runs on every backend start and applies subsequent changes.
