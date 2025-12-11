# DataKern

Data ingestion module for geOrchestra

## Prerequisites

- Python 3.12
- Node 22.20.0+

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
# Launch all services + GeoServer + GeoNetwork + frontend + backend
make up-full

# If you want to re-build airflow external libs (data-manipulation):
make reload-airflow-deps
```

## Dev environment setup:

If you want to run backend and frontend separately for development purposes, you can setup the development environment:

Running services:
```bash
# Launch all services (Airflow + gateway + ldap)
make up-light

# In light mode, you can launch backend and frontend with docker but you will need to change the gateway config to right hosts in docker/datadir/gateway/routes.yaml to use docker internal hostnames:
# georchestra.gateway.services:
# backend.target: http://datakern-backend:8000/ Use this line
# backend.target: http://host.docker.internal:8000/ Comment this line
# frontend.target: http://datakern-frontend:8080/ Use this line
# frontend.target: http://host.docker.internal:4200/frontend/ Comment this line
# airflow.target: http://airflow-apiserver:8081/airflow Use this line
# airflow.target: http://localhost:8081/airflow Comment this line

# Then launch the backend:
make run-backend

# And in another terminal, launch the frontend:
cd apps/frontend && npm install && npm start

# If you want to re-build airflow external libs (data-manipulation):
make reload-airflow-deps
```

## Application Access

### Gateway for the Authentication

The DataKern application is accessible through a gateway that handles authentication and routing to the frontend and backend services.

- **URL**: http://localhost:8080/
- **Credentials**: `testadmin/testadmin`

It redirects, by default, to the frontend at http://localhost:8080/datakern/.

### Frontend

The DataKern frontend is built with Angular 20 and provides the user interface for managing data ingestion workflows. It features a modern, component-based architecture using Tailwind CSS for styling.

- **Gateway URL**: http://localhost:8080/datakern/
- **URL**: http://localhost:8001/

For detailed information about the frontend application structure, development setup, and guidelines, see the [frontend README](./apps/frontend/README.md).

### Backend

The DataKern backend is built with FastAPI and serves as the core API for data ingestion operations.

- **Gateway URL**: http://localhost:8080/datakern-backend/
- **Direct URL**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs

### Airflow ELT

The ELT application uses Apache Airflow for data orchestration and workflow management.

- **URL**: http://localhost:8080/airflow
- **Direct URL**: http://localhost:8081
- **Airflow API Documentation**: http://localhost:8081/docs
- **Credentials**: `airflow/airflow`

### GeoServer and GeoNetwork

These services are included in the full setup of DataKern for geospatial data management.

- **GeoServer URL**: http://localhost:8080/geoserver
- **GeoNetwork URL**: http://localhost:8080/geonetwork

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.