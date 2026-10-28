# Adding a source database

The **Database** import source type lets users import a table or a SQL query from an external PostgreSQL
database (see [Importing a dataset](../../user_guide/importing_data.md)). This feature only shows up in the
frontend once at least one source database is configured.

Two types of source database can be declared in `SOURCE_DATABASES`:

- `copy`: the tables are copied into the data database by Airflow (sections 1 to 3 below);
- `direct_access`: GeoServer publishes the tables in place, without copy (see [Direct access](#direct-access)).

Wiring up a `copy` source database requires configuring the **same connection twice**, once for the backend and once
for Airflow, matched by the same key:

- the backend uses it to run the query that lets the user pick a table/write a SQL query, and to know which
  source database keys to show in the UI;
- Airflow uses it to actually read the data during the `staging_dag` run.

## 1. Backend: declare the connection

Add a `copy` entry to `SOURCE_DATABASES` in [`datafeeder.env`](backend.md), a JSON object mapping a key to
an entry whose `connection_string` is a SQLAlchemy/PostgreSQL URI:

```
SOURCE_DATABASES={"SOURCE_DB_1": {"type": "copy", "connection_string": "postgresql://<user>:<password>@<host>:<port>/<database>"}}
```

The key (`SOURCE_DB_1` above) is arbitrary but must be unique and must match the Airflow connection ID
configured in the next step.

!!! warning "Current limitation"

    Only the first `copy` entry of `SOURCE_DATABASES` is used by the backend today (see `apps/backend/src/core/db.py`).
    The JSON format allows several keys, but only single-source-database setups are supported for now.

## 2. Airflow: declare the matching connection

The `staging_dag` reads the source database through an [Airflow
Connection](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html)
whose ID is the same key used in `SOURCE_DATABASES` (see `get_source_sql_engine` in `apps/elt/dags/utils.py`).

### Docker Compose setup

The bundled Airflow uses a file-based secrets backend
(`AIRFLOW__SECRETS__BACKEND: airflow.secrets.local_filesystem.LocalFilesystemBackend`) pointed at
`docker/datadir/datafeeder/airflow/files/conn.json`. Add the same key/URI pair there:

```json
{
  "DATA_PG": "postgresql://postgres:mypassword@datadb/postgres",
  "DATAFEEDER_PG": "postgresql://georchestra:georchestra@database/georchestra",
  "SOURCE_DB_1": "postgresql://<user>:<password>@<host>:<port>/<database>"
}
```

`DATA_PG` and `DATAFEEDER_PG` are the ELT's own built-in connections (the data and Datafeeder application
databases); leave them as-is and only add/edit your `SOURCE_DB_*` entries.

### Other Airflow deployments

Add a `Postgres`-type connection whose **Conn Id** matches the `SOURCE_DATABASES` key, either from the Airflow
UI (Admin > Connections) or with the CLI:

```
airflow connections add 'SOURCE_DB_1' \
    --conn-type postgres \
    --conn-host <host> --conn-port <port> \
    --conn-login <user> --conn-password <password> \
    --conn-schema <database>
```

## 3. Restart

Restart the backend so it picks up the new `SOURCE_DATABASES` value, and restart/redeploy Airflow (scheduler and
API server) so it reloads `conn.json` (or the connection you added).

## Direct access

A `direct_access` source database is not copied: GeoServer reads its tables in place, through a JNDI connection
pool. Airflow is not involved, so no `conn.json` entry is needed. Wiring it up takes three steps: a JNDI
resource in GeoServer, the GeoServer environment variables, and a `SOURCE_DATABASES` entry for the backend.

### 1. GeoServer: declare the JNDI resource

Add a resource to GeoServer's `jetty-env.xml` (in the geOrchestra datadir, `geoserver/jetty-env.xml`; in the
Docker Compose setup, `docker/datadir/geoserver/jetty-env.xml`):

```xml
<New id="patrimoine" class="org.eclipse.jetty.plus.jndi.Resource">
  <Arg>jdbc/patrimoine</Arg>
  <Arg>
    <New class="org.apache.commons.dbcp.BasicDataSource">
      <Set name="driverClassName">org.postgresql.Driver</Set>
      <Set name="username"><Env name="PATRIMOINE_PGUSER"/></Set>
      <Set name="password"><Env name="PATRIMOINE_PGPASSWORD"/></Set>
      <Set name="url">jdbc:postgresql://<Env name="PATRIMOINE_PGHOST"/>:<Env name="PATRIMOINE_PGPORT" default="5432"/>/<Env name="PATRIMOINE_PGDATABASE"/></Set>
      <Set name="defaultReadOnly">true</Set>
      <Set name="validationQuery">SELECT 1</Set>
      <Set name="maxWait">10000</Set>
      <Set name="maxActive">10</Set>
      <Set name="maxIdle">5</Set>
      <Set name="minIdle">1</Set>
      <Set name="accessToUnderlyingConnectionAllowed">true</Set>
    </New>
  </Arg>
</New>
```

The first `<Arg>` (`jdbc/patrimoine`) is the JNDI name: it must be exactly the `jndi_reference` of the
`SOURCE_DATABASES` entry (step 3), since the datastores created by Datafeeder point to it.

### 2. GeoServer: environment variables and restart

The `<Env name="..."/>` elements are read from GeoServer's environment. Set them for the GeoServer container or
process; in the Docker Compose setup, the `geoserver` service reads them from `docker/.envs-database-georchestra`:

```
PATRIMOINE_PGDATABASE=patrimoine
PATRIMOINE_PGHOST=sourcedb_direct_access
PATRIMOINE_PGPORT=5432
PATRIMOINE_PGUSER=patrimoine_reader
PATRIMOINE_PGPASSWORD=patrimoine_reader_password
```

The host and port are the ones GeoServer reaches the database at (here the Docker service name and its internal
port). `jetty-env.xml` is only read at startup, so restart GeoServer (`docker compose restart geoserver`) after
changing it or its variables.

### 3. Backend: declare the connection

Add a `direct_access` entry to `SOURCE_DATABASES` in [`datafeeder.env`](backend.md):

```
SOURCE_DATABASES={"PATRIMOINE": {"type": "direct_access", "connection_string": "postgresql://patrimoine_reader:patrimoine_reader_password@localhost:5435/patrimoine", "jndi_reference": "jdbc/patrimoine", "roles": ["ADMINISTRATOR"], "label": "Patrimoine (monuments de Lille)"}}
```

- `connection_string` is only used by the backend to list the schemas and tables shown in the wizard, so its
  user only needs read access (`CONNECT`, `USAGE` on the schemas, `SELECT` on the tables). It can be a different
  user from the JNDI pool one, and the host/port are the ones the backend reaches the database at, which can
  differ from GeoServer's (`localhost:5435` from the host vs `sourcedb_direct_access:5432` inside Docker above).
- `jndi_reference` is the JNDI name declared in step 1.
- `roles` lists the geOrchestra roles (without the `ROLE_` prefix) allowed to create datasets on this database;
  when empty, only administrators can.
- `label` is the name shown in the wizard (optional, the key is shown when absent).

Restart the backend so it picks up the new value.

### Tables in the geOrchestra database

When the tables to publish already live in a database GeoServer has a pool for, such as the local geOrchestra
database behind `jdbc/geodata` (`GEODATA_PG*` variables), steps 1 and 2 can be skipped: set `jndi_reference` to
`jdbc/geodata` and point `connection_string` at the same database. Keep in mind that this pool's user usually
has more than read access.

### Superset

Superset does not go through GeoServer's JNDI pool: to build charts or dashboards on a direct access database,
declare a database connection for it in Superset as well.
