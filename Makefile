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

up: ## Start all services using Docker Compose
	docker compose up -d --wait

run-backend: install-python ## Run the backend application
	uv run fastapi dev apps/backend/src/main.py --reload --host 0.0.0.0

docker-build-backend: ## Build the backend Docker image
	docker build -f Dockerfile.backend --target development -t backend:dev .

docker-build-airflow: ## Build the Airflow Docker image
	docker build -f Dockerfile.airflow --target development -t apache/airflow:dev .

docker-run-backend: docker-build-backend ## Run the backend Docker container (with hot-reloading)
	docker run -p 8000:8000 -v ./pyproject.toml:/app/pyproject.toml -v ./uv.lock:/app/uv.lock -v ./libs:/app/libs -v ./apps:/app/apps backend:dev

docker-run-airflow: docker-build-airflow ## Run the Airflow Docker container
	docker compose up -d --wait airflow-apiserver

.PHONY: default help clean-python install-python check-all-python fix-all-python up run-backend docker-build-backend docker-build-airflow docker-run-backend docker-run-airflow