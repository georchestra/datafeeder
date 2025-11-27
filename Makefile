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
	(uv run poe lint)
	(uv run poe fmt)
	(uv run poe check)

fix-all-python: install-python ## Fix all issues: linting and formatting
	(uv run poe lint:fix)
	(uv run poe fmt:fix)

run-backend: install-python ## Run the backend application
	uv run fastapi dev apps/backend/src/main.py --reload

docker-build-backend: install-python ## Build the backend Docker image
	docker build -f Dockerfile.backend --target development -t backend:dev .

docker-run-backend: install-python ## Run the backend Docker container (with hot-reloading)
	docker run -p 8000:8000 -v ./pyproject.toml:/app/pyproject.toml -v ./uv.lock:/app/uv.lock -v ./libs:/app/libs -v ./apps:/app/apps backend:dev

.PHONY: default help clean-python install-python check-all-python fix-all-python run-backend docker-build-backend docker-run-backend