## 1. Configuration & connexions

- [ ] 1.1 [P] Remplacer `POSTGRES_SOURCE_*` par `SOURCE_DATABASES: dict[str, str]` dans `apps/backend/src/core/config.py` — champ avec default `{}`, parsé depuis JSON string env var
- [ ] 1.2 [P] Mettre à jour `apps/backend/src/services/settings_service.py` — feature flag `database_source` basé sur `len(SOURCE_DATABASES) > 0`
- [ ] 1.3 [P] Mettre à jour `docker/datadir/datafeeder-python/datafeeder.env` — remplacer les `POSTGRES_SOURCE_*` par `SOURCE_DATABASES='{"SOURCE_DB_1": "postgresql://postgres:mypassword@datadb:5432/postgres"}'`
- [ ] 1.4 [P] Ajouter `SOURCE_DB_1` dans `docker/datadir/datafeeder-python/airflow/files/conn.json` — URI vers la BDD source (même datadb en dev)
- [ ] 1.5 [P] Ajouter `get_source_sql_engine(db_key: str)` dans `apps/elt/dags/utils.py` — `PostgresHook(db_key).get_sqlalchemy_engine()` (la clé Airflow = la clé `SOURCE_DATABASES`)

---

## 2. Fonction d'ingestion data_manipulation

- [ ] 2.1 Implémenter `ingest_data_from_database_into_postgis()` dans `libs/data_manipulation/src/data_manipulation/ingestion.py` — lit la table source (détection géo/non-géo), écrit dans staging via `write_data_to_postgis()`
- [ ] 2.2 [P] Ajouter les tests unitaires pour `ingest_data_from_database_into_postgis()` dans `libs/data_manipulation/tests/` — cas nominal géo, non-géo, table inexistante, schéma inexistant
- [ ] 2.3 [P] Mettre à jour `staging.py` — construire `source_url` au format `db://{db_key}/{schema}/{table}` (en v1 : première clé de `SOURCE_DATABASES` via `get_settings()`) et adapter le title fallback dans `get_staging_metadata`

---

## 3. Tâche Airflow

- [ ] 3.1 Ajouter le case `"DATABASE"` dans le branching de `apps/elt/dags/task_groups/ingestion.py` — `do_branching()` retourne `database_ingest_step`
- [ ] 3.2 Implémenter `database_ingest_step` dans `apps/elt/dags/task_groups/ingestion.py` — parse `source` (`db://{db_key}/{schema}/{table}`), appelle `ingest_data_from_database_into_postgis()` avec `get_source_sql_engine(db_key)` et `get_data_sql_engine()`
- [ ] 3.3 Ajouter `database_ingest_step` dans le wiring du task group (`do_branching() >> [... , database_ingest_step()]`)
- [ ] 3.4 Ajouter `"DATABASE"` dans l'enum `source_type` du `process_dag.py` params — sans ça, la recurrence est cassée (`apps/elt/dags/process_dag.py:60`)

---

## 4. Tests backend

- [ ] 4.1 [P] Mettre à jour les tests de `settings_service` dans `apps/backend/tests/services/test_settings_service.py` — tester le feature flag avec `SOURCE_DATABASES` au lieu de `POSTGRES_SOURCE_*`
- [ ] 4.2 [P] Mettre à jour les tests de config dans `apps/backend/tests/` — vérifier le parsing de `SOURCE_DATABASES`
- [ ] 4.3 [P] Mettre à jour les tests staging database dans `apps/backend/tests/api/routes/test_staging_database.py` — adapter les fixtures de config si nécessaire
- [ ] 4.4 [P] Mettre à jour les assertions d'URL dans `test_staging_database.py` — `"db://geo/rivers"` → `"db://SOURCE_DB_1/geo/rivers"` et `"db://geo/parcels"` → `"db://SOURCE_DB_1/geo/parcels"` (nouveau format `db://{db_key}/{schema}/{table}`)

---

## 5. Documentation & config externe (hors scope code)

- [ ] 5.1 Mettre à jour la config dans `argocd_gs_mel_apps` (repo MEL externe) — ajouter `SOURCE_DATABASES` côté backend et une connexion Airflow `SOURCE_DB_1` (même clé des deux côtés) (à confier à Flo)
