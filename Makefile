# Display help message by default
default: help

help: ## Display this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "    %-30s%s\n", $$1, $$2}'

clean-python: ## Clean uv cache and lock file
	uv run poe clean

install-python: ## Install all dependencies using uv
	uv run poe install

check-all-python: install-python ## Run all checks: linting, formatting, and type checking
	-uv run poe lint
	-uv run poe fmt
	-uv run poe check

fix-all-python: install-python ## Fix all issues: linting and formatting
	-uv run poe lint:fix
	-uv run poe fmt:fix

build-libs: install-python ## Build all shared libraries
	uv build libs/data_manipulation

up-light: build-libs ## Start all services using Docker Compose
	docker compose up -d --wait --build

up-full: build-libs ## Start all services including GeoServer and GeoNetwork using Docker Compose
	docker compose --profile geoserver --profile geonetwork up -d --wait --build

down: ## Stop all services using Docker Compose
	docker compose down

reload-airflow-deps: build-libs ## Reload Airflow DAG processor with updated dependencies
	docker compose down airflow-dag-processor &&
	docker compose up -d --build --wait airflow-dag-processor

run-backend: install-python ## Run the backend application
	uv run fastapi dev apps/backend/src/main.py --reload --host 0.0.0.0

docker-build-backend: ## Build the backend Docker image
	echo "TODO: Implement backend Docker build"

docker-build-frontend: ## Build the frontend Docker image
	echo "TODO: Implement frontend Docker build"

.PHONY: default help clean-python install-python check-all-python fix-all-python build-libs up-light up-full down reload-airflow-deps run-backend docker-build-backend docker-build-frontend