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

## geOrchestra platform

Datafeeder is a geOrchestra module: it expects to run behind a geOrchestra **Gateway** (authentication, routing) and
integrates with:

- **PostgreSQL/PostGIS**, for its own metadata (the `datafeeder` schema) and for staged/final dataset tables
- **GeoServer**, to publish layers
- **GeoNetwork**, to hold the datasets' metadata records
- **Apache Airflow**, as the task execution engine for the ingestion pipelines

The provided Docker Compose setup bundles a minimal geOrchestra stack (gateway, LDAP, database) together with
Airflow, so you don't need a pre-existing geOrchestra platform to try Datafeeder out.
