## Purpose

Modifications de la configuration backend pour passer d'une connexion source unique (`POSTGRES_SOURCE_*`) à un dictionnaire `EXTERNAL_DATABASES` extensible.

## MODIFIED Requirements

### Requirement: Source database connection configuration (P1)
Le backend DOIT supporter un dictionnaire `EXTERNAL_DATABASES` de type `dict[str, str]` dans `Settings`, où chaque clé est un identifiant logique et chaque valeur est une URI de connexion PostgreSQL (format SQLAlchemy). Le dictionnaire est fourni comme JSON string via variable d'environnement. En v1, une seule entrée est utilisée (`EXTERNAL_DB_1`). La feature database source est considérée comme disponible lorsque `EXTERNAL_DATABASES` contient au moins une entrée.

Les variables `POSTGRES_SOURCE_HOST`, `POSTGRES_SOURCE_PORT`, `POSTGRES_SOURCE_USER`, `POSTGRES_SOURCE_PASSWORD`, `POSTGRES_SOURCE_DB` sont supprimées et remplacées par `EXTERNAL_DATABASES`.

#### Scenario: EXTERNAL_DATABASES configuré avec une entrée
- **WHEN** `EXTERNAL_DATABASES='{"EXTERNAL_DB_1": "postgresql://user:pass@host:5432/db"}'`
- **THEN** la feature database source est disponible
- **AND** `"database_source"` est inclus dans `enabled_features`

#### Scenario: EXTERNAL_DATABASES vide ou absent
- **WHEN** `EXTERNAL_DATABASES` n'est pas défini ou est un dictionnaire vide `{}`
- **THEN** la feature database source n'est pas disponible
- **AND** `"database_source"` n'est PAS inclus dans `enabled_features`

#### Scenario: EXTERNAL_DATABASES avec plusieurs entrées (future-proof)
- **WHEN** `EXTERNAL_DATABASES='{"EXTERNAL_DB_1": "postgresql://...", "EXTERNAL_DB_2": "postgresql://..."}'`
- **THEN** la feature database source est disponible
- **AND** en v1, seule la première entrée est utilisée implicitement

### Requirement: Database source feature flag in settings (P1)
L'endpoint `GET /settings` DOIT inclure `"database_source"` dans le tableau `enabled_features` lorsque `EXTERNAL_DATABASES` contient au moins une entrée non-vide.

#### Scenario: Feature flag present when EXTERNAL_DATABASES configured
- **WHEN** `EXTERNAL_DATABASES` contient au moins une entrée avec une URI non-vide
- **THEN** `GET /settings` retourne `enabled_features` contenant `"database_source"`

#### Scenario: Feature flag absent when EXTERNAL_DATABASES empty
- **WHEN** `EXTERNAL_DATABASES` est vide ou non défini
- **THEN** `GET /settings` retourne `enabled_features` sans `"database_source"`
