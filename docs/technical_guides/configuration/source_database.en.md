# Adding a source database

The **Database** import source type lets users import a table or a SQL query from an external PostgreSQL
database (see [Importing a dataset](../../user_guide/importing_data.md)). This feature only shows up in the
frontend once at least one source database is configured.

Wiring up a source database requires configuring the **same connection twice**, once for the backend and once
for Airflow, matched by the same key:

- the backend uses it to run the query that lets the user pick a table/write a SQL query, and to know which
  source database keys to show in the UI;
- Airflow uses it to actually read the data during the `staging_dag` run.

## 1. Backend: declare the connection

Add an entry to `SOURCE_DATABASES` in [`datafeeder.env`](backend.md), a JSON object mapping a key to a
SQLAlchemy/PostgreSQL URI:

```
SOURCE_DATABASES={"SOURCE_DB_1": "postgresql://<user>:<password>@<host>:<port>/<database>"}
```

The key (`SOURCE_DB_1` above) is arbitrary but must be unique and must match the Airflow connection ID
configured in the next step.

!!! warning "Current limitation"

    Only the first entry of `SOURCE_DATABASES` is used by the backend today (see `apps/backend/src/core/db.py`).
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
webserver) so it reloads `conn.json` (or the connection you added).
