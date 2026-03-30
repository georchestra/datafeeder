## Why

Le tunnel d'ingestion supporte actuellement les fichiers (upload, URL, FTP) comme sources de données. La MEL a besoin d'ingérer des données directement depuis des tables d'une base de données PostgreSQL existante (la "base DataMEL"). Le type `DATABASE` existe déjà dans l'enum `ImportType` et les specs frontend/backend sont déjà implémentées (sélection UI, validation, endpoint staging, feature flag). Il manque la brique ELT (tâche Airflow) et la configuration de connexion pour que le pipeline fonctionne de bout en bout.

## What Changes

- **Configuration backend** : remplacer les 5 variables `POSTGRES_SOURCE_*` par un dictionnaire `SOURCE_DATABASES` (clé/valeur `str:str`) dans la config backend, avec une entrée `SOURCE_DB_1` pointant vers la connexion `pg_data`
- **Connexion Airflow** : ajouter dans `conn.json` la connexion vers la BDD externe définie ci-dessus
- **Tâche Airflow** : ajouter une branche `database_ingest_step` dans le task group `ingestion` (branching sur `source_type == "DATABASE"`), qui copie la table source vers staging
- **Fonction data_manipulation** : ajouter `ingest_data_from_database_into_postgis()` dans `libs/data_manipulation` pour lire une table distante et l'écrire en staging (via pandas `read_sql_table` → `write_data_to_postgis`)
- **Résolution source** : le backend doit pouvoir retrouver à partir de l'`IntegrityLink` la BDD cible, le schéma et la table (le `source_url` encode `db://{db_key}/{schema}/{table}`, la BDD est résolue via la config `SOURCE_DATABASES`)
- **Config ArgoCD** : mettre à jour la config dans `argocd_gs_mel_apps` (repo MEL externe — à confier à Flo)

## Capabilities

### New Capabilities
- `db-ingestion-elt`: Tâche Airflow et fonction data_manipulation pour copier une table depuis une BDD externe vers staging. Inclut la configuration des connexions (backend `SOURCE_DATABASES`, Airflow `conn.json`).

### Modified Capabilities
- `database-source-backend`: La résolution de la BDD source passe d'une connexion unique (`POSTGRES_SOURCE_*`) à un dictionnaire `SOURCE_DATABASES`. Le `source_url` encode désormais l'identifiant de la BDD en plus du schema/table : `db://SOURCE_DB_1/schema/table`.

## Impact

- **apps/elt/** : nouveau task dans `task_groups/ingestion.py`, mise à jour du branching, nouvelle connexion Airflow
- **libs/data_manipulation/** : nouvelle fonction d'ingestion depuis BDD
- **apps/backend/src/core/config.py** : remplacement `POSTGRES_SOURCE_*` par `SOURCE_DATABASES`
- **apps/backend/src/api/routes/ingestion/staging.py** : adaptation de la résolution de connexion BDD
- **docker/datadir/datafeeder-python/datafeeder.env** : nouvelles variables d'environnement
- **conn.json (Airflow)** : nouvelle entrée de connexion
- **Repo externe argocd_gs_mel_apps** : mise à jour config K8s (hors scope code, à confier à Flo)
- **Données non-géo** : le pipeline doit fonctionner aussi bien avec des données géographiques que non-géographiques (déjà supporté par le pipeline de transformation existant)
