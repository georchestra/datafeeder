# Datafeeder

Data ingestion module for geOrchestra - supports CSV, GeoPackage, GeoJSON, Zipped-Shapefile, Parquet, GeoParquet files & OGC services, FTP, Database. 

## Prerequisites

- Python 3.12
- Node 22.20.0+
- Docker & Docker Compose

You can use the provided Makefile to manage the development environment and run common tasks. `make help` is self-explanatory.

First install uv:

```bash
# Install uv if you don't have it yet
curl -LsSf https://astral.sh/uv/install.sh | sh
# verify that uv is usable
uv --version
```

## Docker quick-start

Then, you can setup the development environment:
```
Running services:
```bash
# Launch all services + GeoServer + GeoNetwork
make up

# Then launch the backend:
make run-backend

# And in another terminal, launch the frontend:
cd apps/frontend && npm install && npm start
```

`libs/data_manipulation` is bind-mounted into the Airflow containers, so source edits are picked up live. After changing `libs/data_manipulation/pyproject.toml` dependencies, rebuild with `docker compose up -d --build`.

## Application Access

### Gateway for the Authentication

The Datafeeder application is accessible through a gateway that handles authentication and routing to the frontend and backend services.

- **URL**: http://localhost:8080/
- **Credentials**: `testadmin/testadmin`

It redirects, by default, to the frontend at http://localhost:8080/datafeeder/.

### Frontend

The Datafeeder frontend is built with Angular 20 and provides the user interface for managing data ingestion workflows. It features a modern, component-based architecture using Tailwind CSS for styling.

- **Gateway URL**: http://localhost:8080/datafeeder/
- **URL**: http://localhost:8001/

For detailed information about the frontend application structure, development setup, and guidelines, see the [frontend README](./apps/frontend/README.md).

### Backend

The Datafeeder backend is built with FastAPI and serves as the core API for data ingestion operations.

- **Gateway URL**: http://localhost:8080/datafeeder-backend/
- **Direct URL**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs

### Airflow ELT

The ELT application uses Apache Airflow for data orchestration and workflow management.

- **URL**: http://localhost:8080/airflow
- **Direct URL**: http://localhost:8081
- **Airflow API Documentation**: http://localhost:8081/docs
- **Credentials**: `airflow/airflow`

### Task Executors: Airflow 

DataKern only supports one task execution engines: **Airflow** (default) and. 

- **Airflow**: Full-featured workflow orchestration with web UI, suitable for complex workflows

We will consider adding support for other task execution engines in the future based on user feedback and demand.

### GeoServer and GeoNetwork

These services are included in the full setup of Datafeeder for geospatial data management.

- **GeoServer URL**: http://localhost:8080/geoserver
- **GeoNetwork URL**: http://localhost:8080/geonetwork

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.
