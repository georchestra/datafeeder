# Frontend configuration

The Angular frontend talks exclusively to the backend REST API, through a TypeScript client generated from the
backend's OpenAPI schema (`apps/frontend/src/app/core/api/`).

## Pointing at a backend

- In development, the frontend expects the backend on `http://localhost:8000` (see the [quick-start](../installation/quickstart.md)).
- Behind the gateway, requests are routed to the backend at `/datafeeder-backend/`.

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
