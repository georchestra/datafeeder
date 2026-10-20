# Frontend configuration

The Angular frontend talks exclusively to the backend REST API, through a TypeScript client generated from the
backend's OpenAPI schema (`apps/frontend/src/app/core/api/`).

## Pointing at a backend

- In development, the frontend expects the backend on `http://localhost:8000` (see the [quick-start](../installation/quickstart.md)).
- Behind the gateway, requests are routed to the backend at `/datafeeder-backend/`.

## Configuration file (`default.toml`)

At startup the frontend loads `assets/configuration/default.toml`, using the
[geonetwork-ui configuration system](https://geonetwork.github.io/geonetwork-ui/main/docs/guide/configure.html).
The default file is [`apps/frontend/conf/default.toml`](https://github.com/georchestra/datafeeder/blob/main/apps/frontend/conf/default.toml).

Supported sections:

- `[theme]`: `primary_color`, `secondary_color`, `main_color`, `background_color` (mandatory), and optionally
  `main_font`, `title_font`, `fonts_stylesheet_url`, `favicon`
- `[translations.xx]`: overrides of translation keys for language `xx`, for example:

  ```toml
  [translations.fr]
  integrityLinks.dashboard = "Mes jeux de données"
  ```

  They take precedence over both the datafeeder and the geonetwork-ui translations.

The `[theme]` section and its mandatory colors must always be present, otherwise the application does not start.

To use a different file per deployment, set the `CONFIG_DIRECTORY_OVERRIDE` environment variable of the frontend
container to a directory containing a `default.toml`: it replaces the default one when the container starts. In the
docker composition, this is `docker/datadir/datafeeder/frontend/default.toml`, mounted at
`/etc/georchestra/datafeeder/frontend`.

## Regenerating the API client

Whenever the backend's OpenAPI schema changes (new/changed routes or models), the frontend client must be
regenerated:

```bash
# from the repository root, with the backend running
apps/frontend/scripts/generate-api.sh
```

Or manually:

```bash
curl -o openapi.json http://localhost:8000/openapi.json
cd apps/frontend && npm run generate-api
```

Commit the regenerated files. See the [frontend README](https://github.com/georchestra/datafeeder/blob/main/apps/frontend/README.md)
for the full development, testing and Docker workflow.
