## Purpose

Tâche Airflow et fonction data_manipulation pour copier une table depuis une BDD PostgreSQL externe vers le schéma staging. Inclut la configuration des connexions Airflow et la fonction d'ingestion.

## ADDED Requirements

### Requirement: Connexion Airflow SOURCE_DB_1 (P1)
Le fichier `conn.json` DOIT contenir une entrée `SOURCE_DB_1` avec l'URI de connexion vers la BDD externe. Le module `utils.py` des DAGs DOIT exposer une fonction `get_source_sql_engine(db_key: str)` qui retourne un `SQLAlchemy Engine` via `PostgresHook(db_key)`. La clé de connexion Airflow DOIT correspondre à la clé du dictionnaire `SOURCE_DATABASES` du backend.

#### Scenario: Connexion SOURCE_DB_1 disponible
- **WHEN** `conn.json` contient l'entrée `SOURCE_DB_1` avec une URI PostgreSQL valide
- **THEN** `get_source_sql_engine("SOURCE_DB_1")` retourne un `Engine` connecté à la BDD source

#### Scenario: Connexion SOURCE_DB_1 absente
- **WHEN** `conn.json` ne contient pas l'entrée `SOURCE_DB_1`
- **THEN** `get_source_sql_engine("SOURCE_DB_1")` lève une exception Airflow

### Requirement: Fonction ingest_data_from_database_into_postgis (P1)
Le module `libs/data_manipulation/src/data_manipulation/ingestion.py` DOIT exposer une fonction `ingest_data_from_database_into_postgis(source_schema, source_table, source_engine, target_table, target_engine, target_schema)` qui lit une table depuis la BDD source et l'écrit dans le schéma staging de la BDD data via `write_data_to_postgis()`.

#### Scenario: Ingestion d'une table non-géographique
- **WHEN** la table source `public.communes` existe dans la BDD source et ne contient pas de colonne geometry
- **THEN** la fonction lit la table avec `pd.read_sql_table()`
- **AND** écrit les données dans `staging.{target_table}` via `write_data_to_postgis()`
- **AND** les données sont identiques à la source

#### Scenario: Ingestion d'une table géographique
- **WHEN** la table source `geo.rivers` existe dans la BDD source et contient une colonne geometry
- **THEN** la fonction lit la table avec `gpd.read_postgis()`
- **AND** écrit les données dans `staging.{target_table}` via `write_data_to_postgis()`
- **AND** la géométrie est préservée

#### Scenario: Table source inexistante
- **WHEN** la table source `public.inexistant` n'existe pas dans la BDD source
- **THEN** la fonction lève une exception

#### Scenario: Schéma source inexistant
- **WHEN** le schéma source `inexistant` n'existe pas dans la BDD source
- **THEN** la fonction lève une exception

### Requirement: Tâche Airflow database_ingest_step (P1)
Le task group `ingestion` DOIT inclure un case `"DATABASE"` dans le branching qui appelle `ingest_data_from_database_into_postgis()`. La tâche DOIT parser le paramètre `source` (format `db://{db_key}/{schema}/{table}`) pour extraire la clé BDD, le schéma et la table source.

#### Scenario: Branching vers database_ingest_step
- **WHEN** le DAG staging est déclenché avec `source_type=DATABASE` et `source=db://SOURCE_DB_1/geo/rivers`
- **THEN** le branching sélectionne `database_ingest_step`
- **AND** la tâche parse `source` pour extraire `db_key=SOURCE_DB_1`, `schema=geo` et `table=rivers`
- **AND** la tâche appelle `ingest_data_from_database_into_postgis()` avec le `source_engine` depuis `get_source_sql_engine("SOURCE_DB_1")` et le `target_engine` depuis `get_data_sql_engine()`
- **AND** la table est copiée dans `staging.{staging_table_name}`

#### Scenario: Staging table name depuis params
- **WHEN** le DAG est déclenché avec `staging_table_name` dans les params
- **THEN** la tâche utilise ce nom comme table cible dans staging

#### Scenario: Staging table name depuis XCom (recurrence)
- **WHEN** le DAG process est en mode refresh avec `source_type=DATABASE`
- **AND** `staging_table_name` n'est pas dans les params
- **THEN** la tâche récupère le nom depuis XCom (`generate_staging_table_name`)

#### Scenario: Source URL mal formée
- **WHEN** le paramètre `source` ne respecte pas le format `db://{db_key}/{schema}/{table}`
- **THEN** la tâche lève une `AirflowException`

### Requirement: Pipeline de bout en bout identique aux autres sources (P1)
Après l'écriture en staging par `database_ingest_step`, le reste du pipeline (transformation, écriture finale, callbacks) DOIT se dérouler exactement comme pour les autres types de source (FILE, URL, FTP). Aucune modification du pipeline post-staging n'est nécessaire.

#### Scenario: Transformation après ingestion BDD
- **WHEN** les données d'une table BDD ont été ingérées en staging
- **AND** le DAG process est déclenché avec une `IntegrityTransformation`
- **THEN** les transformations sont appliquées (rename, cast, filter, projection)
- **AND** les données transformées sont écrites dans le schéma final
- **AND** la table staging est nettoyée

#### Scenario: Aperçu des données après ingestion BDD
- **WHEN** les données d'une table BDD ont été ingérées en staging
- **THEN** l'endpoint `GET /ingestion/staging/{id}/preview` retourne un aperçu des données
- **AND** l'endpoint `GET /ingestion/staging/{id}/metadata` retourne les métadonnées (colonnes, row_count)

#### Scenario: Recurrence avec source BDD
- **WHEN** un dataset avec `source_import_type=DATABASE` a un schedule configuré
- **AND** le DAG process est déclenché en mode refresh
- **THEN** Airflow ré-ingère depuis la BDD source vers un nouveau staging
- **AND** le pipeline de transformation s'exécute normalement
