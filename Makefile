# Display help message by default
default: help

help: ## Display this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "    %-30s%s\n", $$1, $$2}'

clean-python: ## Clean uv cache and lock file
	uv run poe clean

install-python: ## Install all dependencies using uv + write current user's UID into .env
	uv run poe install
	@grep -q '^AIRFLOW_UID=' .env && sed -i 's/^AIRFLOW_UID=.*/AIRFLOW_UID='"$$(id -u)"'/' .env || printf 'AIRFLOW_UID=%s\n' "$$(id -u)" >> .env

fix-and-check-all-python: install-python ## Fix all issues: linting and formatting
	-uv run poe lint:fix
	-uv run poe fmt:fix
    -uv run poe check --verbose

test-libs: install-python ## Run library tests with pytest
	cd libs/data_manipulation && uv run pytest tests/ -v

test-backend: install-python ## Run backend tests with pytest
	cd apps/backend && uv run pytest tests/ -v

test-backend-coverage: install-python ## Run backend tests with coverage report
	cd apps/backend && uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

build-libs: install-python ## Build all shared libraries
	uv build libs/data_manipulation

up-light: build-libs ## Start all services using Docker Compose
	docker compose up -d --wait --build

up-full: build-libs ## Start all services including GeoServer and GeoNetwork using Docker Compose
	docker compose --profile geoserver --profile geonetwork up -d --wait --build

down: ## Stop all services using Docker Compose
	docker compose --profile geoserver --profile geonetwork down

down-v: ## Stop all services and remove volumes using Docker Compose
	docker compose --profile geoserver --profile geonetwork down -v

run-backend: install-python ## Run the backend application
	cd apps/backend && \
	DATAFEEDER_CONFIG="$(CURDIR)/apps/backend/datafeeder.env" sh -c \
	  'uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir ../../apps/backend --reload-dir ../../libs'

docker-build-backend: ## Build the backend Docker image
	echo "TODO: Implement backend Docker build"

docker-build-frontend: ## Build the frontend Docker image
	echo "TODO: Implement frontend Docker build"

.PHONY: default help clean-python install-python check-all-python fix-all-python build-libs up-light up-full down down-v run-backend docker-build-backend docker-build-frontend

