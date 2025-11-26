#! /usr/bin/env bash
set -euxo pipefail

BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
OPENAPI_FILE="openapi.json"

cd "$BACKEND_DIR"
mv "$OPENAPI_FILE" "$FRONTEND_DIR/"
python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > "../$OPENAPI_FILE"
cd ..
mv "$OPENAPI_FILE" "$FRONTEND_DIR/"
cd "$FRONTEND_DIR"
npm run generate-api