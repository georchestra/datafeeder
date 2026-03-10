# Datafeeder frontend

The new (geo) data ingestion plateform.

## 🚀 Quickstart

**Note:** The frontend requires the backend to be running on port 8000. See the [main README](../../README.md) for backend setup instructions.

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
apps/frontend/scripts/generate-api.sh
```

* Commit the changes.

### Manually

* Start the Docker Compose stack or start the standalone backend.

* Download the OpenAPI JSON file from `http://localhost:8000/openapi.json` and copy it to a new file `openapi.json` at the root of the `frontend` directory.

```bash
curl -o openapi.json http://localhost:8000/openapi.json
```

* To generate the frontend client, run:

```bash
npm run generate-api
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

## 🐳 Docker

### Build the Docker image

From the frontend directory:

```bash
docker build -t datafeeder-frontend:latest .
```

### Run the Docker container

```bash
docker run -p 4200:8080 datafeeder-frontend:latest
```

The frontend will be available at http://localhost:4200

### Using Docker Compose

From the project root directory:

```bash
# Build and start the frontend service
docker-compose up frontend

# Or rebuild and start
docker-compose up --build frontend
```
