# Docker quick-start

A `Makefile` is provided to manage the development environment; `make help` lists every available target.

!!! tip "Full geOrchestra platform"

    This guide uses Datafeeder's own developer-oriented Docker Compose setup. To try Datafeeder as part of a full
    geOrchestra platform (all modules, published images), use the `master` branch of
    [georchestra/docker](https://github.com/georchestra/docker), which bundles Datafeeder support.


## Application access

### Gateway (authentication)

- **URL**: <http://localhost:8080/>
- **Credentials**: `testadmin/testadmin`

The gateway redirects, by default, to the frontend at <http://localhost:8080/datafeeder/>.

### Frontend

- **Gateway URL**: <http://localhost:8080/datafeeder/>

See the [frontend README](https://github.com/georchestra/datafeeder/blob/main/apps/frontend/README.md) for
development details.

### Backend

- **Gateway URL**: <http://localhost:8080/datafeeder-backend/>
- **API documentation**: <http://localhost:8000/docs>

### Airflow (ELT)

- **Gateway URL**: <http://localhost:8080/airflow>
- **Credentials**: `airflow/airflow`

### GeoServer and GeoNetwork

Included in the full Docker Compose setup for geospatial data management:

- **GeoServer**: <http://localhost:8080/geoserver>
- **GeoNetwork**: <http://localhost:8080/geonetwork>
