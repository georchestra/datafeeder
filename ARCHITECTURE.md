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

## Components

- **Backend**: A REST API built with FastAPI that handles data ingestion requests, validation, and processing.
- **Frontend**: An Angular-based user interface that allows users to manage data ingestion tasks 
- **ELT Workflows**: Airflow is used to define and manage data ingestion workflows, including extraction, loading, and transformation of data.
- **Shared Library**: A Python library that contains common data manipulation functions used by both the backend and ELT workflows.

## Fonctionnement minimal (en français)

DataKern doit être pensé en "API first" et, si possible, indépendant de n'importe quel outil.  

Le fonctionnement minimum viable de DataKern repose sur l'interaction entre deux composants principaux : 
- Le backend (et sa bdd) qui expose une API REST pour gérer les demandes d'ingestion de données.
- Les Dags Airflow qui utilisent la BDD du backend pour récupérer les tâches d'ingestion à exécuter.

Geoserver et geonetwork sont des composants optionnels qui peuvent être intégrés pour enrichir les fonctionnalités de DataKern, mais ne devraient pas être indispensables à son fonctionnement de base.
L'interface utilisateur (frontend) est également un composant optionnel qui facilite la gestion des tâches d'ingestion, mais l'API REST du backend doit être pleinement fonctionnelle et accessible indépendamment de l'interface utilisateur.

