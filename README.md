# DataKern

Data ingestion module for geOrchestra


## Dev environment setup:

You can use the provided Makefile to manage the development environment and run common tasks. `make help` is self-explanatory.

Running services:
```bash
# Launch all services (Airflow + gateway + ldap)
make up-light

# Or launch all services + GeoServer + GeoNetwork + frontend + backend
make up-full

# In light mode, you can launch backend and frontend separately:
make run-backend
cd apps/frontend && npm start

# If you want to re-build airflow external libs (data-manipulation):
make reload-airflow-deps
```

## Application Access

### Gateway for the Authentication

The DataKern application is accessible through a gateway that handles authentication and routing to the frontend and backend services.

- **URL**: http://localhost:8080/
- **Credentials**: `testadmin/testadmin`

### Frontend

The DataKern frontend is built with Angular 20 and provides the user interface for managing data ingestion workflows. It features a modern, component-based architecture using Tailwind CSS for styling.

- **Gateway URL**: http://localhost:8080/datakern/
- **URL**: http://localhost:8080/

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