# Kubernetes / Helm installation

This section covers deploying Datafeeder on an **existing geOrchestra platform** (Gateway, Console/LDAP, GeoServer,
GeoNetwork already running), using the [`datafeeder-python` Helm
chart](https://github.com/georchestra/helm-charts/tree/main/datafeeder-python). It complements the
[Configuration](../configuration/index.md) section: read that first to understand each setting, this page focuses on
the steps and gotchas specific to a Kubernetes/production deployment (outside of the Docker Compose dev setup). See
[Component interactions](../presentation.md#component-interactions) for a diagram of how the pieces below talk to
each other.

## 1. Databases

See [Databases](../configuration/databases.md) for why Datafeeder uses three separate PostgreSQL databases, and
for the schemas/extensions/scripts that must be applied to each **before the first install** (Alembic's baseline
migration assumes the schema already exists — it doesn't bootstrap it).

### The chart doesn't create a secret for the "data" database

The chart auto-generates a `<release>-database-backend` secret for the georchestra/backend DB (falling back to the
bundled Airflow PostgreSQL's credentials if `backend.database.existingSecret` is unset). **There is no equivalent
for the data database**: `backend.data_db.existingSecret` has no default and no template creates a
`<release>-database-data` secret for you. If you leave it unset, the backend pod will fail to start
(`CreateContainerConfigError`, missing secret `<release>-database-data`).

Either point `backend.data_db.existingSecret` at an existing secret (e.g. the same one as
`backend.database.existingSecret`, if data and georchestra share the same database), or create it yourself:

```bash
kubectl create secret generic <release>-database-data \
  --from-literal=host=<host> --from-literal=port=5432 \
  --from-literal=dbname=<data-db-name> \
  --from-literal=user=<user> --from-literal=password=<password>
```

## 2. Platform accounts

Two distinct accounts are involved — don't confuse them:

### GeoServer / GeoNetwork: use a dedicated privileged LDAP account

The backend calls GeoServer and GeoNetwork **through the Gateway** (`GEOSERVER_INTERNAL_URL` /
`GEONETWORK_INTERNAL_URL` must be Gateway URLs — that's where LDAP authentication happens), so it needs an LDAP
account with enough rights to create workspaces/layers and publish metadata.

Nothing in the chart creates this account for you — it must exist beforehand as a real LDAP user, with the
`backend.config.geoserver.username` / `geonetwork.username` settings pointing at its `uid` and real password.
Every geOrchestra platform already has a privileged technical LDAP account used internally by several modules (see
the [datadir README](https://github.com/georchestra/datadir/blob/master/README.md)), and it's tempting to reuse it
for Datafeeder too — but prefer creating a **separate, dedicated** account instead: sharing one privileged account
across modules means rotating its password (or revoking it) affects all of them at once, and makes it harder to
tell which module did what from the audit trail. A placeholder username will fail — it must be a real, existing
LDAP user either way.

### Airflow REST API: a separate, Airflow-only account

`backend.config.airflow.username` / `password` authenticate the backend against **Airflow's own** FAB auth
manager — this has nothing to do with LDAP/geOrchestra accounts. That Airflow user is created by the Airflow
sub-chart's `createUserJob`, from `airflow.createUserJob.defaultUser` (default: `admin` / `admin`). Ignore
`webserver.defaultUser` in the sub-chart's values: it's the Airflow 2 way of setting this, explicitly marked
deprecated in favor of `createUserJob`, and has no effect on Airflow 3.

**This is the most common source of the `401` / `Login Failed for user: admin` error** seen in the backend logs
when uploading a dataset: the chart's default `backend.config.airflow.password` (`change-me`) does not match the
Airflow sub-chart's default user password (`admin`), because nothing in the chart wires the two together. Set both
explicitly to the same value:

```yaml
backend:
  config:
    airflow:
      username: admin
      password: <same-value>

airflow:
  createUserJob:
    defaultUser:
      password: <same-value>
```

!!! tip "With ArgoCD: enable `createUserJob`, sync once, then disable it again"

    `createUserJob` is a Helm-hook Job — left permanently enabled, ArgoCD tends to keep the Application stuck
    `OutOfSync` on it (Jobs are immutable once created, so ArgoCD can never converge a diff against it on
    subsequent syncs). The practical workaround: temporarily set `airflow.createUserJob.enabled: true`, sync so the
    Job runs and creates the Airflow user, then set it back to `false` and sync again so ArgoCD stops trying to
    reconcile it. If the user still doesn't exist afterwards (check with `airflow users list`), create it by hand
    instead: exec into an Airflow pod and run `airflow users create ...`.

## 3. Airflow Connections (`AIRFLOW_CONN_*`)

Any `AIRFLOW_CONN_<CONN_ID>` environment variable injected into the Airflow pods (via the sub-chart's `airflow.secret`
list, or any other means) is automatically parsed by Airflow itself into a Connection with id `<CONN_ID>` — this is
plain [Airflow behavior](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html#storing-connections-in-environment-variables),
not geOrchestra-specific wiring:

| Connection | Required? | Purpose |
|---|---|---|
| `AIRFLOW_CONN_DATA_PG` | **Yes** | The data database (staging/final tables) |
| `AIRFLOW_CONN_DATAFEEDER_PG` | **Yes** | The georchestra/`datafeeder` schema database |
| `AIRFLOW_CONN_SOURCE_DB_1` | Only if using the **Database** source type | See [adding a source database](../configuration/source_database.md) |
| `AIRFLOW_CONN_LOGS_S3` | No — platform-specific (e.g. shipping task logs to S3) | Not needed for a default deployment |

!!! tip "The secret key must hold the full URI, not separate fields"

    Each `AIRFLOW_CONN_*` `secretKeyRef` must resolve to **one key containing the complete connection URI**
    (`postgresql://user:password@host:port/dbname`) — Airflow doesn't assemble it from separate fields the way the
    backend's `PGHOST`/`PGUSER`/`PGPASSWORD`/... env vars do (see `_helpers-database.tpl`). If your database secret
    only exposes discrete `host`/`port`/`user`/`password`/`dbname` keys (e.g. the one backing
    `backend.database.existingSecret`/`backend.data_db.existingSecret`), it won't work as-is for an
    `AIRFLOW_CONN_*` var — add a dedicated key holding the pre-built URI instead, and point the Airflow connection
    at that key. In practice this often means adding one `connection_url`-style key per database to whatever
    Secret already carries its discrete fields.

## 4. Exposing Airflow

The chart sets Airflow's `api.base_url` to `/airflow`, but does **not** expose it: there's no `airflow-ingress` template in
`datafeeder-python`, and `airflow.ingress.apiServer.enabled` is `false` by default. You need to either:

- enable `airflow.ingress.apiServer.enabled: true` (and configure hosts/annotations under `airflow.ingress`), or
- add a route for `/airflow` in your geOrchestra **Gateway** configuration, pointing at the
  `<release>-airflow-api-server` service — the same way GeoServer/GeoNetwork routes are declared.

## 5. Sizing: Airflow worker memory

Don't go below the chart's default `airflow.workers.resources.limits.memory` (`5Gi`, see the
[prerequisites](prerequisites.md) sizing table). Setting it too low (e.g. `2Gi`) can make even the worker's own
**liveness probe** push memory usage over the limit and get the pod OOM-killed — not just actual ingestion
workloads. `4Gi` is a reasonable floor if you need to shrink it; raise it further for large/complex ingestions.

## 6. The `airflow-logs-pvc` needs to be wired up manually

The chart provisions a `<release>-airflow-logs-pvc` PersistentVolumeClaim (`templates/airflow-logs-pvc.yaml`, sized
via `volumes.airflow_logs`), but by default **nothing points Airflow at it**. Left as-is, actual task log storage
falls back to the Airflow sub-chart's own `airflow.logs` settings, which this chart defaults to a **RAM-backed
`emptyDir`** (`airflow.logs.emptyDirConfig: {sizeLimit: 1Gi, medium: Memory}`): logs don't survive the worker pod
restarting, and count against its memory limit.

!!! warning "This isn't purely cosmetic"

    When a `staging_dag`/`process_dag` run fails, the frontend lets the user download that run's logs — the
    backend fetches them from Airflow on demand (`GET /dags/{dag_id}/runs/{dag_run_id}/logs`, see
    [`airflow_logs.py`](https://github.com/georchestra/datafeeder/blob/main/apps/backend/src/services/airflow_logs.py)),
    it doesn't store them itself. If the worker pod that ran the failed task has since restarted (redeploy,
    autoscaling, OOM, ...), those logs are gone and the download simply fails — with an ephemeral, memory-backed
    volume this can happen well before anyone gets a chance to click the button.

Point Airflow's own log persistence at the PVC the chart already provisions, rather than leaving it unreferenced:

```yaml
airflow:
  logs:
    persistence:
      enabled: true
      existingClaim: <release>-airflow-logs-pvc
```
