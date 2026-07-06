# Configuration

Keep in mind the components presented in the [Presentation section](../presentation.md), it will help you understand
how the pieces interact with each other.

You will need to configure:

1. The [backend](backend.md): PostgreSQL database, GeoServer/GeoNetwork endpoints, source databases, secrets.
1. The [ELT](elt.md): the Airflow deployment executing the DAGs, and the `AIRFLOW_STAGING_TIMEOUT_SECONDS` setting.
1. The [frontend](frontend.md): which backend to talk to.

If you run into trouble along the way, see the [Troubleshooting section](../troubleshooting.md).
