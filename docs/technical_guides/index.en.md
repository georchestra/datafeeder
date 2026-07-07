# Install guide

Datafeeder is a monorepo made of a backend API, a frontend SPA and an Airflow-based ELT pipeline, sharing one
PostgreSQL database and a Python library.

There are 3 distinct steps in setting up Datafeeder:

- Deploy the **backend** and its PostgreSQL database, and configure it for your platform (GeoServer, GeoNetwork,
  source databases, task executor)
- Deploy the ELT engine (**Airflow**) with the Datafeeder DAGs
- Optionally, deploy the **frontend** for a UI (the backend REST API works standalone)

Read the [presentation](presentation.md) first to understand how the components interact, then follow
[Installation](installation/index.md) and [Configuration](configuration/index.md).
