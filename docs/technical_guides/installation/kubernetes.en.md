# Kubernetes / Helm installation

This page covers deploying Datafeeder on an **existing geOrchestra platform** (Gateway, Console/LDAP, GeoServer,
GeoNetwork) with the [`datafeeder-python` Helm chart](https://github.com/georchestra/helm-charts/tree/main/datafeeder-python).
Read [Configuration](../configuration/index.md) first for the meaning of each setting; this page only lists the
Kubernetes-specific steps and gotchas.

## 1. Databases

Run the [initialization scripts](../configuration/databases.md#initialization-scripts) before the first install.

The chart generates a `<release>-database-backend` secret, but **none for the data database**: if
`backend.data_db.existingSecret` is unset, the backend pod fails with `CreateContainerConfigError`. Point it at an
existing secret (e.g. the same as `backend.database.existingSecret` if both share a database), or create it:

```bash
kubectl create secret generic <release>-database-data \
  --from-literal=host=<host> --from-literal=port=5432 \
  --from-literal=dbname=<data-db-name> \
  --from-literal=user=<user> --from-literal=password=<password>
```

## 2. Platform accounts

### GeoServer / GeoNetwork: a dedicated LDAP account

The backend calls GeoServer and GeoNetwork **through the Gateway** (`GEOSERVER_INTERNAL_URL` /
`GEONETWORK_INTERNAL_URL` must be Gateway URLs), so `backend.config.geoserver.username` / `geonetwork.username` must
be a real LDAP user allowed to create layers and publish metadata. The chart does not create it. Prefer a dedicated
account over reusing the platform's shared technical account, so it can be rotated and audited independently.

### Airflow REST API: an Airflow-only account

`backend.config.airflow.username` / `password` authenticate against **Airflow's own** user, created by the
sub-chart's `createUserJob` from `airflow.createUserJob.defaultUser` (default `admin` / `admin`; ignore the
deprecated `webserver.defaultUser`). The chart's default backend password (`change-me`) doesn't match, which causes
`401` / `Login Failed for user: admin` on upload. Set both to the same value:

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

!!! tip "With ArgoCD"

    `createUserJob` is an immutable Helm-hook Job that keeps the Application `OutOfSync`. Enable it, sync once,
    then disable it and sync again. If the user is still missing (`airflow users list`), create it with
    `airflow users create ...` from an Airflow pod.

## 3. Airflow Connections

Airflow turns every `AIRFLOW_CONN_<CONN_ID>` env var (e.g. from the sub-chart's `airflow.secret` list) into a
Connection ([Airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html#storing-connections-in-environment-variables)):

| Connection | Required? | Purpose |
|---|---|---|
| `AIRFLOW_CONN_DATA_PG` | **Yes** | Data DB |
| `AIRFLOW_CONN_DATAFEEDER_PG` | **Yes** | geOrchestra DB (`datafeeder` schema) |
| `AIRFLOW_CONN_SOURCE_DB_1` | Only for the **Database** source type | See [adding a source database](../configuration/source_database.md) |
| `AIRFLOW_CONN_LOGS_S3` | No | Platform-specific (e.g. S3 log shipping) |

!!! tip "One secret key with the full URI"

    Each `secretKeyRef` must point to a single key holding the complete URI
    (`postgresql://user:password@host:port/dbname`). Secrets exposing only discrete `host`/`user`/`password`/...
    keys (like those used by the backend) need an extra key with the pre-built URI.

## 4. Exposing Airflow

The chart sets Airflow's `api.base_url` to `/airflow` but doesn't expose it (`airflow.ingress.apiServer.enabled` is
`false`). Either enable that ingress, or add a `/airflow` route in the geOrchestra **Gateway** pointing at the
`<release>-airflow-api-server` service.

## 5. Airflow worker memory

Keep `airflow.workers.resources.limits.memory` at its `5Gi` default (see [prerequisites](prerequisites.md)), `4Gi`
at the very least: with e.g. `2Gi`, the liveness probe alone can get the worker OOM-killed.

## 6. Airflow logs persistence

The chart provisions a `<release>-airflow-logs-pvc`, but nothing uses it: logs go to a RAM-backed `emptyDir` by
default, count against the worker's memory limit, and are lost when the pod restarts. Since the frontend lets users
download failed-run logs, fetched from Airflow on demand, those downloads then fail. Wire the PVC up:

```yaml
airflow:
  logs:
    persistence:
      enabled: true
      existingClaim: <release>-airflow-logs-pvc
```

## 7. Restricting Airflow egress (optional)

The chart ships no NetworkPolicy. Airflow pods (label `release: <release>`) only need to reach:

- DNS (`kube-dns`, port 53);
- the other Airflow components (`tier: airflow`);
- the backend on port `8000` (DAG callbacks, `BACKEND_INTERNAL_URL`);
- the PostgreSQL databases (or their pgbouncer);
- the public internet, for **URL** / **WFS** sources — excluding private ranges so that user-supplied URLs can't
  reach internal services.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: datafeeder-airflow-egress
spec:
  podSelector:
    matchLabels:
      release: <release>
  policyTypes: [Egress]
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
  - to:
    - podSelector:
        matchLabels:
          tier: airflow
          release: <release>
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/instance: <release>
          app.kubernetes.io/component: <release>-backend
    ports:
    - {protocol: TCP, port: 8000}
  - to:
    - ipBlock:
        cidr: <db-ip>/32  # or a podSelector if PostgreSQL runs in the cluster
    ports:
    - {protocol: TCP, port: 5432}
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16]
```
