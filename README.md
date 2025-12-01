# DataKern

Data ingestion module for geOrchestra


## Dev environment setup: 

You can use the provided Makefile to manage the development environment and run common tasks. `make help` is self-explanatory.

Running services:
```bash
# Launch all services
make up

# Launch only the backend app
make run-backend

# Launch only the frontend app
make run-frontend

# Launch only the ELT (Airflow) app
make docker-run-airflow
```

## Application Access

### Frontend

The DataKern frontend is built with Angular 20 and provides the user interface for managing data ingestion workflows. It features a modern, component-based architecture using Tailwind CSS for styling.

- **URL**: http://localhost:8080/
- **Credentials**: `testadmin/testadmin`

For detailed information about the frontend application structure, development setup, and guidelines, see the [frontend README](./apps/frontend/README.md).

### Backend

The DataKern backend is built with FastAPI and serves as the core API for data ingestion operations.

- **Gateway URL**: TODO
- **Direct URL**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs

### Airflow

The ELT application uses Apache Airflow for data orchestration and workflow management.

- **URL**: http://localhost:8080/airflow
- **Direct URL**: http://localhost:8081
- **Airflow API Documentation**: http://localhost:8081/docs
- **Credentials**: `airflow/airflow`

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.
