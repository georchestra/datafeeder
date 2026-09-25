# Configuration

Keep in mind the components presented in the [Presentation section](../presentation.md), it will help you understand
how the pieces interact with each other.

You will need to configure:

1. The [backend](backend.md): PostgreSQL database, GeoServer/GeoNetwork endpoints, source databases, secrets.
2. The [template](template.md): the reference template for record creation, where specific content fields are dynamically replaced.
3. The [ELT](elt.md): the Airflow deployment executing the DAGs, and the `AIRFLOW_STAGING_TIMEOUT_SECONDS` setting.
4. The [frontend](frontend.md): which backend to talk to.
5. Optionally, a [source database](source_database.md) to enable the **Database** import source type.

If you run into trouble along the way, see the [Troubleshooting section](../troubleshooting.md).
