# DataKern Architecture

## Overview

DataKern is a data ingestion module for geOrchestra built as a monorepo.

## Project Structure

```
DataKern/
├── apps/
│   ├── backend/          # REST API for data ingestion (FastAPI/Python)
│   ├── frontend/         # User interface for data management (Angular/ custom gn-ui application)
│   └── elt/              # Extract, Load, Transform workflows (Airflow)
├── libs/
│   └── data_manipulation/  # Shared library for backend and elt (Python/Pandas/GeoPandas)
├── Makefile              # Lint, test, build and run commands
└── docker-compose.yml    # Orchestrates all services
```
