## Context

Le tunnel d'ingestion supporte actuellement FILE, URL et FTP comme sources. Le type `DATABASE` existe dans l'enum `ImportType`, le frontend et le backend (endpoint staging, validation, feature flag) sont déjà implémentés. Il manque :

1. La brique ELT : une tâche Airflow `database_ingest_step` dans le task group `ingestion`
2. La fonction `ingest_data_from_database_into_postgis()` dans `libs/data_manipulation`
3. La configuration des connexions : backend (`SOURCE_DATABASES`) + Airflow (`conn.json`)
4. La résolution de la BDD source depuis l'`IntegrityLink`

Le pipeline existant suit le pattern : raw → staging → transformation → final. L'ingestion depuis BDD doit s'insérer dans ce même pipeline, la seule différence étant la source de données (table PostgreSQL distante au lieu d'un fichier/URL).

## Goals / Non-Goals

**Goals:**
- Permettre à Airflow de copier une table d'une BDD PostgreSQL externe vers le schéma staging
- Réutiliser le pipeline de transformation existant (staging → final) sans modification
- Configurer les connexions de manière centralisée et extensible (dictionnaire `SOURCE_DATABASES`)
- Supporter les données géographiques ET non-géographiques
- Fonctionner en dev (docker-compose) et en prod (K8s)

**Non-Goals:**
- Support de plusieurs BDD simultanément (v1 : une seule BDD configurée, mais l'architecture est extensible)
- Support d'autres SGBD que PostgreSQL
- Requêtes SQL custom (on copie une table entière, pas de SELECT arbitraire)
- Gestion de la config ArgoCD/K8s (hors scope code, à confier à Flo)
- Modifications du frontend (déjà implémenté)

## Decisions

### D1 : Configuration backend — dictionnaire `SOURCE_DATABASES`

**Choix** : Remplacer les 5 variables `POSTGRES_SOURCE_*` par un champ unique `SOURCE_DATABASES: dict[str, PostgresDsn]` dans `Settings`. Chaque entrée est une paire clé = identifiant logique, valeur = URI de connexion PostgreSQL validée par Pydantic (ex: `SOURCE_DB_1=postgresql://user:pass@host:5432/db`).

**Rationale** : Le format dictionnaire est extensible (plusieurs BDD à terme) tout en restant simple pour la v1 (une seule entrée). L'URI de connexion est le format standard SQLAlchemy, déjà utilisé pour `POSTGRES_DATA_URI`.

**Alternatives considérées** :
- Garder les 5 variables `POSTGRES_SOURCE_*` : non extensible, 5 variables par BDD
- Un fichier de config séparé (YAML/JSON) : overhead inutile, les env vars suffisent

**Impact sur le feature flag** : `database_source` est dans `enabled_features` si `SOURCE_DATABASES` contient au moins une entrée.

**Format env var** : `SOURCE_DATABASES='{"SOURCE_DB_1": "postgresql://user:pass@host:5432/db"}'` (JSON string parsée par Pydantic).

### D2 : Format du `source_url` dans IntegrityLink

**Choix** : Adopter le format `db://{db_key}/{schema}/{table}` (ex: `db://SOURCE_DB_1/geo/rivers`). L'identifiant de la BDD est explicite dans l'URL, ce qui permet de résoudre la bonne connexion côté Airflow quand plusieurs BDD seront supportées.

**Rationale** : Rend le `source_url` auto-suffisant — on peut retrouver la BDD, le schéma et la table sans dépendre d'un contexte implicite. Le backend construit l'URL avec la clé de la BDD (en v1 : `SOURCE_DB_1`, seule entrée du dictionnaire). Côté Airflow, la tâche parse l'URL et résout la connexion.

**Impact** : Nécessite de modifier le parsing existant dans `staging.py` (`db://{schema}/{table}` → `db://{db_key}/{schema}/{table}`) et le titre fallback dans `get_staging_metadata`.

**Alternatives considérées** :
- `db://{schema}/{table}` (format actuel) : plus simple mais la BDD est implicite, non extensible

### D3 : Connexion Airflow pour la BDD source

**Choix** : Les connexions Airflow pour les BDD sources utilisent les **mêmes clés** que le dictionnaire `SOURCE_DATABASES` du backend. En v1 : `SOURCE_DB_1` dans `conn.json` (dev) et comme secret K8s/Helm (prod). La tâche Airflow extrait le `db_key` de l'URL et utilise `PostgresHook(db_key)` pour obtenir le `SQLAlchemy Engine`.

**Rationale** : Aligner les clés backend et Airflow élimine tout mapping intermédiaire. Ajouter une 2e BDD = ajouter une entrée dans `SOURCE_DATABASES` + une connexion Airflow du même nom. Zéro changement de code.

**Nouveaux utilitaires dans `utils.py`** :
```python
def get_source_sql_engine(db_key: str) -> Engine:
    return PostgresHook(db_key).get_sqlalchemy_engine()
```

**Pattern côté backend** : Le module `db.py` initialise au démarrage un `source_engine` et `source_db_key` à partir de la première (et unique en v1) entrée de `SOURCE_DATABASES`. Ces deux constantes sont importées directement dans `staging.py`, évitant d'appeler une fonction sur chaque requête.

```python
# db.py
source_db_key, _source_db_value = next(iter(get_settings().SOURCE_DATABASES.items()), (None, None))
source_engine = create_engine(str(_source_db_value), ...) if _source_db_value else None
```

### D4 : Fonction d'ingestion `ingest_data_from_database_into_postgis()`

**Choix** : Nouvelle fonction dans `libs/data_manipulation/src/data_manipulation/ingestion.py` qui :
1. Parse le `source_url` (`db://{db_key}/{schema}/{table}`) pour extraire la clé BDD, schema et table
2. Lit la table source via `pd.read_sql(select(table), ...)` / `gpd.read_postgis()` depuis le `source_engine` (utilise `Table(..., autoload_with=source_engine)` pour inspecter le schéma)
3. Écrit dans staging via `write_data_to_postgis()` existant sur le `target_engine`

**Signature** :
```python
def ingest_data_from_database_into_postgis(
    source_schema: str,
    source_table: str,
    source_engine: Engine,
    target_table: str,
    target_engine: Engine,
    target_schema: str = "public",
) -> None
```

**Rationale** : Deux engines distincts (source et target) car la BDD source est différente de la BDD data. Le pattern suit celui des autres fonctions d'ingestion qui finissent toutes par appeler `write_data_to_postgis()`.

**Gestion géo/non-géo** : On détecte la présence d'une colonne geometry dans la table source. Si présente → `gpd.read_postgis()`, sinon → `pd.read_sql_table()`. C'est le même pattern que `read_data_from_postgis()` existant.

### D5 : Tâche Airflow `database_ingest_step`

**Choix** : Ajouter un case `"DATABASE"` dans le branching du task group `ingestion` qui appelle `ingest_data_from_database_into_postgis()`.

**Paramètres DAG** : Le `source` du DAG contient `db://{db_key}/{schema}/{table}`. La tâche parse cette URL, obtient le `source_engine` via `get_source_sql_engine(db_key)`, et le `target_engine` via `get_data_sql_engine()` existant.

**Pattern identique** aux autres ingest steps : récupération du `staging_table_name` depuis params ou XCom, appel de la fonction d'ingestion, écriture dans staging.

### D6 : Environnement de développement

**Choix** : En dev (docker-compose), `SOURCE_DB_1` pointe vers la même base `datadb` que `DATA_PG` (les données de test sont pré-chargées dans cette base). Le `conn.json` est mis à jour avec l'entrée `SOURCE_DB_1`.

**Côté backend** : `SOURCE_DATABASES` contient `SOURCE_DB_1` pointant vers `datadb`.

## Risks / Trade-offs

**[Risque] Pas de pagination pour les grandes tables** → En v1, `pd.read_sql_table()` charge toute la table en mémoire. Acceptable car les tables DataMEL sont de taille raisonnable. Si besoin futur, on pourra ajouter un chunking par batch.

**[Info] Architecture multi-BDD prête** → Le format `source_url` (`db://{db_key}/{schema}/{table}`), le dictionnaire `SOURCE_DATABASES` côté backend, et la résolution Airflow via `get_source_sql_engine(db_key)` sont alignés sur la même clé. Ajouter une 2e BDD = ajouter une entrée dans `SOURCE_DATABASES` + une connexion Airflow du même nom. Aucun changement de code nécessaire.

**[Trade-off] Pas de credentials chiffrés pour la BDD source** → Contrairement aux sources URL/FTP où l'utilisateur saisit des credentials, la connexion BDD est pré-configurée par l'admin via la config. Les credentials sont dans l'URI de connexion (env var / secret K8s), pas dans l'IntegrityLink.

**[Trade-off] Copie intégrale de la table** → Pas de filtrage à la source (WHERE clause). Le filtrage se fait au niveau transformation (après staging), comme pour les autres types de source. Cohérent avec le principe "mêmes tuyaux pour tous les scénarios".
