# Datakern frontend

The new (geo) data ingestion plateform.

## 🚀 Quickstart

Start the frontend app in dev mode:

```sh
npx nx serve
# or
npm run start
```

## 🔧 Scripts

To create a production bundle:

```sh
npm run build
```

To generate TypeScript client from OpenAPI specification:

```sh
npm run generate-api
```

## 🌏 Generate Angular API client

### Automatically

* Activate the backend virtual environment.
* From the top level project directory, run the script:

```bash
./scripts/generate-client.sh
```

* Commit the changes.

### Manually

* Start the Docker Compose stack.

* Download the OpenAPI JSON file from `http://localhost:8000/api/v1/openapi.json` and copy it to a new file `openapi.json` at the root of the `frontend` directory.

* To generate the frontend client, run:

```bash
npm run generate-client
```

* Commit the changes.

Notice that everytime the backend changes (changing the OpenAPI schema), you should follow these steps again to update the frontend client.

## 💉 Testing

To launch unit tests (Vitest):

```sh
npm run test:ut
```


To launch end-to-end tests (Cypress):

```sh
npm run test:e2e
# or
npm run test:e2e:ci # headless mode specially used by the ci
```
