## Purpose

Modifications de la configuration backend pour passer d'une connexion source unique (`POSTGRES_SOURCE_*`) à un dictionnaire `SOURCE_DATABASES` extensible.

## MODIFIED Requirements

### Requirement: Source database connection configuration (P1)
Le backend DOIT supporter un dictionnaire `SOURCE_DATABASES` de type `dict[str, str]` dans `Settings`, où chaque clé est un identifiant logique et chaque valeur est une URI de connexion PostgreSQL (format SQLAlchemy). Le dictionnaire est fourni comme JSON string via variable d'environnement. En v1, une seule entrée est utilisée (`SOURCE_DB_1`). La feature database source est considérée comme disponible lorsque `SOURCE_DATABASES` contient au moins une entrée.

Les variables `POSTGRES_SOURCE_HOST`, `POSTGRES_SOURCE_PORT`, `POSTGRES_SOURCE_USER`, `POSTGRES_SOURCE_PASSWORD`, `POSTGRES_SOURCE_DB` sont supprimées et remplacées par `SOURCE_DATABASES`.

#### Scenario: SOURCE_DATABASES configuré avec une entrée
- **WHEN** `SOURCE_DATABASES='{"SOURCE_DB_1": "postgresql://user:pass@host:5432/db"}'`
- **THEN** la feature database source est disponible
- **AND** `"database_source"` est inclus dans `enabled_features`

#### Scenario: SOURCE_DATABASES vide ou absent
- **WHEN** `SOURCE_DATABASES` n'est pas défini ou est un dictionnaire vide `{}`
- **THEN** la feature database source n'est pas disponible
- **AND** `"database_source"` n'est PAS inclus dans `enabled_features`

#### Scenario: SOURCE_DATABASES avec plusieurs entrées (future-proof)
- **WHEN** `SOURCE_DATABASES='{"SOURCE_DB_1": "postgresql://...", "SOURCE_DB_2": "postgresql://..."}'`
- **THEN** la feature database source est disponible
- **AND** en v1, seule la première entrée est utilisée implicitement

### Requirement: Database source feature flag in settings (P1)
L'endpoint `GET /settings` DOIT inclure `"database_source"` dans le tableau `enabled_features` lorsque `SOURCE_DATABASES` contient au moins une entrée non-vide.

#### Scenario: Feature flag present when SOURCE_DATABASES configured
- **WHEN** `SOURCE_DATABASES` contient au moins une entrée avec une URI non-vide
- **THEN** `GET /settings` retourne `enabled_features` contenant `"database_source"`

#### Scenario: Feature flag absent when SOURCE_DATABASES empty
- **WHEN** `SOURCE_DATABASES` est vide ou non défini
- **THEN** `GET /settings` retourne `enabled_features` sans `"database_source"`

### Requirement: Staging endpoint source_url format (P1)
L'endpoint `POST /ingestion/staging` et `PUT /ingestion/staging/{id}` DOIVENT construire le `source_url` au format `db://{db_key}/{schema}/{table}` lorsque `type=database`. En v1, la clé BDD est la première (unique) clé du dictionnaire `SOURCE_DATABASES`.

#### Scenario: Construction du source_url avec clé BDD
- **WHEN** `POST /ingestion/staging` est appelé avec `type=database`, `db_schema=geo`, `db_table=rivers`
- **AND** `SOURCE_DATABASES` contient `SOURCE_DB_1`
- **THEN** `source_url` est défini à `db://SOURCE_DB_1/geo/rivers`

#### Scenario: Title fallback pour source DATABASE
- **WHEN** `integrity_title` est NULL et `source_url` est `db://SOURCE_DB_1/geo/rivers`
- **THEN** le titre affiché est `rivers` (nom de la table extrait du source_url)
