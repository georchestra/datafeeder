# Display help message by default
default: help

# Apache Airflow base image (built locally on Debian Trixie from the official
# Airflow Dockerfile, since apache/airflow only ships bookworm based images).
AIRFLOW_VERSION ?= 3.2.2
AIRFLOW_PYTHON_VERSION ?= 3.13.5
AIRFLOW_BASE_IMAGE ?= georchestra/airflow-base:$(AIRFLOW_VERSION)-trixie
export AIRFLOW_VERSION
export AIRFLOW_BASE_IMAGE

help: ## Display this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "    %-30s%s\n", $$1, $$2}'

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

build-airflow-base: ## Build the Debian Trixie based Apache Airflow base image (from the official Dockerfile)
	@if [ -z "$$(docker images -q $(AIRFLOW_BASE_IMAGE))" ]; then \
	  echo "Building $(AIRFLOW_BASE_IMAGE) (Airflow $(AIRFLOW_VERSION), Python $(AIRFLOW_PYTHON_VERSION) on debian:trixie-slim)..."; \
	  docker build \
	    --build-arg BASE_IMAGE=debian:trixie-slim \
	    --build-arg AIRFLOW_VERSION=$(AIRFLOW_VERSION) \
	    --build-arg AIRFLOW_PYTHON_VERSION=$(AIRFLOW_PYTHON_VERSION) \
	    -t $(AIRFLOW_BASE_IMAGE) \
	    docker/airflow-base; \
	  docker tag $(AIRFLOW_BASE_IMAGE) georchestra/airflow-base:latest; \
	else \
	  echo "$(AIRFLOW_BASE_IMAGE) already present, skipping (run 'docker rmi $(AIRFLOW_BASE_IMAGE)' to rebuild)."; \
	fi

up: build-libs ## Start all services including GeoServer and GeoNetwork using Docker Compose
	docker compose --profile geoserver --profile geonetwork up -d --wait --build

down: ## Stop all services using Docker Compose
	docker compose --profile geoserver --profile geonetwork down

down-v: ## Stop all services and remove volumes using Docker Compose
	docker compose --profile geoserver --profile geonetwork down -v

run-backend: install-python ## Run the backend application
	cd apps/backend && \
	DATAFEEDER_CONFIG="$(CURDIR)/apps/backend/datafeeder.env" sh -c \
	  'uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir ../../apps/backend --reload-dir ../../libs'

.PHONY: default help install-python fix-and-check-all-python build-libs build-airflow-base up down down-v run-backend

