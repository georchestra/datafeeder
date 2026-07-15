# Prerequisites

## Software

- **Python 3.12**
- **Node 22.20.0+**
- **Docker & Docker Compose**
- [**uv**](https://docs.astral.sh/uv/), used to manage the Python workspace:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

## Hardware

Sizing depends on the deployment mode.

### Docker Compose (development / evaluation)

The bundled Docker Compose setup runs every component (gateway, LDAP, PostgreSQL, GeoServer, GeoNetwork, Airflow,
backend, frontend) on a single machine. As a rule of thumb, provision at least:

- **4 CPU cores**
- **8 GB RAM**

### Kubernetes / Helm (production)

For a production Helm deployment, the table below lists the `resources.requests`/`limits` used for Datafeeder's own
components — the backend, the frontend, and the Airflow instance dedicated to the ELT pipelines (including its
Celery broker and metadata database):

| Component                     | CPU request | Memory request | Memory limit |
|--------------------------------|:-----------:|:---------------:|:-------------:|
| Backend                        | 250m        | 256Mi           | 512Mi         |
| Frontend                       | 100m        | 64Mi            | 128Mi         |
| Airflow API server              | 250m        | 512Mi           | 1Gi           |
| Airflow scheduler               | 250m        | 512Mi           | 1Gi           |
| Airflow DAG processor           | 250m        | 512Mi           | 1Gi           |
| Airflow triggerer                | 100m        | 256Mi           | 512Mi         |
| Airflow worker (per replica)      | 500m        | 1Gi             | 5Gi           |
| Airflow Redis (Celery broker)     | 100m        | 128Mi           | 256Mi         |
| Airflow metadata PostgreSQL       | 200m        | 512Mi           | 512Mi         |
| **Total (baseline, 1 worker)**    | **~2 vCPU** | **~3.7 GiB**    | **~10 GiB**   |

!!! note

    Airflow worker limits are intentionally generous: large or complex ingestions (big files, heavy transformations)
    can be memory-hungry. Raise the worker requests/limits, or scale the number of worker replicas, if you process
    large datasets.

    This table doesn't cover GeoServer, GeoNetwork, the geOrchestra Gateway/LDAP, or the PostgreSQL/PostGIS instance
    holding staged/final dataset tables — size those following the wider geOrchestra platform's own recommendations.

## geOrchestra platform

Datafeeder is a geOrchestra module: it expects to run behind a geOrchestra **Gateway** (authentication, routing) and
integrates with:

- **PostgreSQL/PostGIS**, for its own metadata (the `datafeeder` schema) and for staged/final dataset tables
- **GeoServer**, to publish layers
- **GeoNetwork**, to hold the datasets' metadata records
- **Apache Airflow**, as the task execution engine for the ingestion pipelines

The provided Docker Compose setup bundles a minimal geOrchestra stack (gateway, LDAP, database) together with
Airflow, so you don't need a pre-existing geOrchestra platform to try Datafeeder out.
