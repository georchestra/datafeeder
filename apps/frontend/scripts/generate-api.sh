#! /usr/bin/env bash
set -euo pipefail

APPS_DIR="apps"
BACKEND_URL="http://localhost:8000"
FRONTEND_DIR="frontend"
OPENAPI_FILE="openapi.json"

# Check if backend is running
if ! curl -s "$BACKEND_URL/openapi.json" > /dev/null; then
    echo "Error: Backend is not running at $BACKEND_URL"
    echo "Please start the backend first with: uv run fastapi dev apps/backend/src/main.py --reload"
    exit 1
fi

# Download OpenAPI spec from running backend
echo "Downloading OpenAPI spec from backend..."
curl -s "$BACKEND_URL/openapi.json" > "$APPS_DIR/$FRONTEND_DIR/$OPENAPI_FILE"

# Generate the API client
echo "Generating API client..."
cd "$APPS_DIR/$FRONTEND_DIR"
npm run generate-api

echo "API client generated successfully!"
