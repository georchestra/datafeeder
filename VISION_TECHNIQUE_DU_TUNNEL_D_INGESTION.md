# Vision technique du tunnel d'ingestion

Ce document décrit simplement les flux de communication entre les composants (Frontend, Backend, ELT/Airflow) du tunnel d'ingestion DataKern.

## Notes préalables

### Les tables principales

- **`datakern.integrity_link`** : Lien entre staging, données finales et métadonnées

### DAGs Airflow

- **`staging_dag`** : DAG d'ingestion dans une table staging
- **`transformation_dag`** : DAG de transformation des données finales

## Flux du tunnel d'ingestion

### 1. Formulaire d'ingestion

L'utilisateur remplit un formulaire d'ingestion dans le **Frontend** avec :
- Type de source (WFS, CSV, SHP, etc.)
- URL de la source

Puis il demande le chargement de la source.

### 2. Processus d'ingestion 

Le **Backend** reçoit la requête d'ingestion et exécute les étapes suivantes :
  - Génère un `dag_id` et un `dag_run_id` (uuid)
  - Création d'un `integrity_link` (avec pour `id` le `dag_id`).
  - Génère une callback URL pour la fin du DAG (si succès)
    - Pour mettre à jour l'`integrity_link` (avec pour `id` le `dag_id`)
  - Déclenche le DAG `staging_dag` via l'API Airflow (avec les uuid, paramètres fournis et la callback URL)
  - Retourne le `dag_id` et `dag_run_id` au **Frontend**

### 3. Monitoring du statut du DAG

Le **Frontend** poll régulièrement le **Backend** pour obtenir le statut du DAG en cours d'exécution.
Le **Backend** interroge l'API Airflow pour obtenir le statut du DAG (`queued`, `running`, `success`, `failed`) et le retourne au **Frontend**.

### 4. Exécution du DAG de staging côté Airflow

Le DAG `staging_dag` est trigger :
- Download, lecture et ingestion dans une table staging PostgreSQL selon le type de source
  - Utilise la lib `data_manipulation` pour cela
- Appel de la callback vers le **Backend**, si le DAG a réussi

### 5. Callback de fin de DAG de staging côté Backend

Le **Frontend** est notifié que le DAG de staging a réussi via le polling.

### 6. Prévisualisation des données et transformations en local

On passe à la 2ème étape du tunnel d'ingestion.
Le **Frontend** demande au **Backend** un aperçu des données ingérées dans la table staging.
Le **Backend** query la table staging et retourne un échantillon des données, le schéma et les métadonnées associées.
L'utilisateur peut visualiser ce subset et y appliquer des transformations via des paramètres de transformation dans la query :
- Filtrage de colonnes
- Renommage de colonnes
- Projection spatiale

+

Une 3eme étape de récurrence de mise à jour peut être configurée (si ce n'est pas un fichier local).

TODO: à définir plus précisément.

### 7. Configuration finale

L'utilisateur valide la configuration finale dans le **Frontend** en l'envoit au **Backend** :
- Config de rransformation
- Le titre sanitisé (slug / nom de table finale)
- Le schedule (si applicable)

Le **Backend** reçoit cette configuration et exécute les étapes suivantes :
- Créé le layer (via geoserver) + renseigner cette info dans l'integrityLink (dataId)
- Créé la fiche de metadonnée (via geonetwork) et la lier au layer geoserver + renseigner cette info dans l'integrityLink (metadaId)
- Renseigne le schedule de mise à jour dans l'integrityLink

### 8. Transformation finale via le DAG de transformation Airflow

TODO: à définir plus précisément.

### 9. Ingestions récurrentes

- Airflow poll régulièrement la BDD pour détecter les `integrity_link` avec `schedule_enabled = true`
- Création dynamique de DAGs pour chaqu'un de ces `integrity_link`
- Exécution des DAGs de transformation pour mettre à jour les données finales selon le schedule défini

