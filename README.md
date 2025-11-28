# DataKern

Data ingestion module for geOrchestra

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

## Makefile Commands

You can use the provided Makefile to manage the development environment and run common tasks. `make help` is self-explanatory.

## Running dev env: 

Run:
```bash
mkdir -p ./datadir/airflow/logs ./datadir/airflow/plugins ./datadir/airflow/config
make
```

### Airflow: 

Go to http://localhost:8080/airflow login and paswword `airflow/airflow` 

### Backend:

Backend runs locally, but you can access through the gateway at http://localhost:8080/backend/

Go to http://localhost:8080/ login and password `testadmin/testadmin`

### Backend:

Build the backend image:
```
make docker-build-backend
```

Run the backend container (with hot-reloading):
```
make docker-run-backend
```

## Frontend Application

The DataKern frontend is built with Angular 20 and provides the user interface for managing data ingestion workflows. It features a modern, component-based architecture using Tailwind CSS for styling.

For detailed information about the frontend application structure, development setup, and guidelines, see the [frontend README](./apps/frontend/README.md).
