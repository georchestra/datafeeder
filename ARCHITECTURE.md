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

## Fonctionnement minimal

DataKern soit être pensé en "API first" et, si possible, indépendant de n'importe quel outil.  

Le fonctionnement minimum viable de DataKern repose sur l'interaction entre deux composants principaux : 
- Le backend (et sa bdd) qui expose une API REST pour gérer les demandes d'ingestion de données.
- Les Dags Airflow qui utilisent la BDD du backend pour récupérer les tâches d'ingestion à exécuter.

Geoserver et geonetwork sont des composants optionnels qui peuvent être intégrés pour enrichir les fonctionnalités de DataKern, mais ne devraient pas être indispensables à son fonctionnement de base.
L'interface utilisateur (frontend) est également un composant optionnel qui facilite la gestion des tâches d'ingestion, mais l'API REST du backend doit être pleinement fonctionnelle et accessible indépendamment de l'interface utilisateur.

Dans le cas ou ces deux seuls composants sont intégrés, les interactions seraient les suivantes:

*Tunnel d'ingestion minimal*
1. Un utilisateur ou un système externe envoie une requête d'ingestion (fichier, url) de données à l'API REST du backend.
2. Le backend déclenche un DAG Airflow correspondant à la tâche d'ingestion (et récupère le dag run id). Il fournit un endpoint pour suivre l'état de la tâche d'ingestion.
3. Airflow ingère les données dans une table staging dédiée.
4. ---- Le front poll l'état de la tâche d'ingestion via l'API REST du backend. ----
5.
   - Un endpoint permettant de récupérer les N premières données de la table staging est disponible pour prévisualiser les données ingérées.
   - Un endpoint permettant de récupérer certaines listes sont dispo (à définir: CRS ? autre ?)
6. Un endpoint de l'API REST du backend permet de définir la transformation, le nom de table finale... et l'enregistre en bdd (Voir la [structure ici](datadir/database/130-datakern.sql))
   - Si dans la configuration, geonetwork est activé, le backend créé une fiche de métadonnée dans geonetwork.
7. Cette bdd est poll par aiflow qui créer les dags dynamique pour chaque tâche d'ingestion récurrentes.
8. Un tâche générique est utilisée pour les ingestions qui n'ont pas de fréquence définie (ingestion one-shot).

API: 
- *GET /<base_path>/config* : Récupérer la configuration de l'application.
- *PUT /<base_path>/new* : Créer une nouvelle tâche d'ingestion.
- *GET /<base_path>/{task_id}/status* : Récupérer l'état de la tâche d'ingestion. Secured
- *GET /<base_path>/{staging_id}/preview* : Récupérer un aperçu des données ingérées. Secured
- *POST /<base_path>/{task_id}/finalize* : Finaliser la tâche d'ingestion avec les transformations et le nom de la table finale. Secured
- *GET /lists/crs* : Récupérer la liste des systèmes de référence ??

*Management du JDD*

- *POST /<base_path>/<dataset>/ : Met à jour un jeu de données. Secured
- *DELETE /<base_path>/<dataset>/delete* : Supprime un jeu de données. Secured
- *POST /<base_path>/<dataset>/rules* : Définit des règles de gestion pour un jeu de données. Secured

## Fonctionnment du front end 

L'interface utilisateur (frontend) de DataKern est conçue pour faciliter la gestion des tâches d'ingestion de données.

*Tunnel d'ingestion:*
Le tunnel d'ingestion interagit avec le backend en récupérant la configuration de l'app.

1. Le choix de la source et son passage à l'étape suivant déclenche un appel à l'API REST du backend pour créer une nouvelle tâche d'ingestion.
2. Le frontend poll régulièrement l'état de la tâche d'ingestion via un endpoint de l'API REST du backend pour fournir des mises à jour en temps réel à l'utilisateur.
3. A la fin de l'ingestion, le frontend permet à l'utilisateur de prévisualiser les données ingérées en appelant un endpoint spécifique de l'API REST du backend.
4. L'utilisateur peut ensuite définir les transformations et le nom de la table finale via l'interface utilisateur, qui envoie ces informations à l'API REST du backend pour finaliser la tâche.
5. L'utilisateur, après avoir validé, est redirigé vers le tableau de bord (si geonetwork dans la config est actif)