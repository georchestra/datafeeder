---
name: frontend-api-sync
description: Regenerate the frontend Angular TypeScript API client after backend API changes. Use when FastAPI routes, request/response models, query parameters, or any backend change alters the OpenAPI schema. Also use after adding, modifying, or removing backend endpoints. Triggers on backend API changes, openapi.json updates, generate-api, API client regeneration.
metadata: 
  triggers: openapi, openapi.json, generate-api, API client, regenerate client, frontend sync, backend API change, curl openapi, ng-openapi-gen, TypeScript client, update frontend, api routes changed
---

# Frontend API Client Sync

Keep the Angular TypeScript client in sync with the FastAPI backend OpenAPI schema.

## When to Trigger

After any change to:
- FastAPI route definitions (new, modified, or removed endpoints)
- Pydantic request/response models used in routes
- Query parameters, path parameters, or request bodies
- Anything that alters the generated `openapi.json`

## Procedure

Run from the **monorepo root** with the backend venv activated:

```bash
# 1. Start the standalone backend (in a separate terminal)
make run-backend

# 2. Download the fresh spec from the running backend
curl -o apps/frontend/openapi.json http://localhost:8000/openapi.json

# 3. Generate the Angular API client
cd apps/frontend && npm run generate-api

# 4. Format & lint the generated code
npm run format
```

Alternatively, use the helper script (steps 1-3 only, still format manually):

```bash
apps/frontend/scripts/generate-api.sh
```

## Important Notes

- The backend **must** be running before downloading the spec.
- Format the generated code (`npm run format`) — the generator output is not pre-formatted.
- The generated client lives in `apps/frontend/src/app/api/`.
