# Datafeeder Architecture

## Overview

Datafeeder is a data ingestion module for geOrchestra built as a monorepo.

## Project Structure

```
Datafeeder/
├── apps/
│   ├── backend/          # REST API for data ingestion (FastAPI/Python)
│   ├── frontend/         # User interface for data management (Angular/ custom gn-ui application)
│   └── elt/              # Extract, Load, Transform workflows (Airflow)
├── libs/
│   └── data_manipulation/  # Shared library for backend and elt (Python/Pandas/GeoPandas)
├── Makefile              # Lint, test, build and run commands
└── docker-compose.yml    # Orchestrates all services
```

## Components

- **Backend**: A REST API built with FastAPI that handles data ingestion requests, validation, and processing.
- **Frontend**: An Angular-based user interface that allows users to manage data ingestion tasks 
- **ELT Workflows**: Airflow is used to define and manage data ingestion workflows, including extraction, loading, and transformation of data.
- **Shared Library**: A Python library that contains common data manipulation functions used by both the backend and ELT workflows.

## Minimal Viable Architecture

Datafeeder is designed as "API first" and, where possible, independent from any specific tool.

The minimum viable runtime relies on the interaction between two core components:
- The **backend** (and its database) which exposes a REST API to manage data ingestion requests.
- The **Airflow DAGs** which use the backend database to retrieve ingestion tasks to execute.

GeoServer and GeoNetwork are optional components that enrich Datafeeder's capabilities but should not be required for the base runtime.
The **frontend** is likewise optional — it eases the management of ingestion tasks, but the backend REST API must be fully functional and reachable independently of the UI.

