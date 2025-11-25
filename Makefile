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
	uv sync --all-groups

run-backend: install ## Run the backend application
	uv run fastapi dev apps/backend/main.py

lint: install ## Lint Python code with ruff
	uv run ruff check apps/backend libs/data-manipulation

lint-and-fix: install ## Lint Python code with ruff and fix any fixable errors
	uv run ruff check apps/backend libs/data-manipulation --fix

format: install ## Format Python code with ruff
	uv run ruff format apps/backend libs/data-manipulation

.PHONY: default help clean install lint lint-and-fix format
