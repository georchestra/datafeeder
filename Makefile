# Display help message by default
default: help

help: ## Display this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "    %-20s%s\n", $$1, $$2}'

clean: ## Clean uv cache and lock file
	uv cache clean

install: ## Install all dependencies using uv
	uv sync --all-packages

run-backend: install ## Run the backend application
	uv run fastapi dev apps/backend/src/main.py --reload

lint: install ## Lint all 
	(cd ./apps/backend && uv run poe lint)
	(cd ./libs/data_manipulation && uv run poe lint)

format: install ## Format all
	(cd ./apps/backend && uv run poe format)
	(cd ./libs/data_manipulation && uv run poe format)

type-check: install ## Type check all
	(cd ./apps/backend && uv run poe type-check)
	(cd ./libs/data_manipulation && uv run poe type-check)
	
docker-build-backend: install ## Build the backend Docker image
	docker build -f Dockerfile.backend --target development -t backend:dev .

docker-run-backend: install ## Run the backend Docker container (with hot-reloading)
	docker run -p 8000:8000 -v ./pyproject.toml:/app/pyproject.toml -v ./uv.lock:/app/uv.lock -v ./libs:/app/libs -v ./apps:/app/apps backend:dev

.PHONY: default help clean install lint format docker-build-backend docker-run-backend