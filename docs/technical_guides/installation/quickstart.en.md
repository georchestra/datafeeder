# Docker quick-start

A `Makefile` is provided to manage the development environment; `make help` lists every available target.

## Bring up the stack

```bash
# Launch all services, including GeoServer and GeoNetwork
make up

# Then launch the backend:
make run-backend

# And in another terminal, launch the frontend:
cd apps/frontend && npm install && npm start
```

`libs/data_manipulation` is bind-mounted into the Airflow containers, so source edits there are picked up live.
After changing `libs/data_manipulation/pyproject.toml` dependencies, rebuild with `docker compose up -d --build`.

## Application access

### Gateway (authentication)

- **URL**: <http://localhost:8080/>
- **Credentials**: `testadmin/testadmin`

The gateway redirects, by default, to the frontend at <http://localhost:8080/datafeeder/>.

### Frontend

- **Gateway URL**: <http://localhost:8080/datafeeder/>
- **Direct URL**: <http://localhost:8001/>

See the [frontend README](https://github.com/georchestra/datafeeder/blob/main/apps/frontend/README.md) for
development details.

### Backend

- **Gateway URL**: <http://localhost:8080/datafeeder-backend/>
- **Direct URL**: <http://localhost:8000/>
- **API documentation**: <http://localhost:8000/docs>

### Airflow (ELT)

- **Gateway URL**: <http://localhost:8080/airflow>
- **Direct URL**: <http://localhost:8081>
- **API documentation**: <http://localhost:8081/docs>
- **Credentials**: `airflow/airflow`

Datafeeder currently supports a single task execution engine: **Airflow**. Other engines may be added in the
future based on demand.

### GeoServer and GeoNetwork

Included in the full Docker Compose setup for geospatial data management:

- **GeoServer**: <http://localhost:8080/geoserver>
- **GeoNetwork**: <http://localhost:8080/geonetwork>
