# Vision technique du tunnel d'ingestion

Ce document décrit simplement les flux de communication entre les composants (Frontend, Backend, ELT/Airflow) du tunnel d'ingestion DataKern.

## Notes préalables

### Les tables principales

- **`datakern.integrity_link`** : Lien entre staging, données finales et métadonnées

### DAGs Airflow

- **`staging_dag`** : DAG d'ingestion d'un dataset dans une table staging
- **`process_dag`** : DAG de transformation et d'ingestion d'un dataset dans la table finale

## Flux du tunnel d'ingestion

### 1. Formulaire d'ingestion

L'utilisateur remplit un formulaire d'ingestion dans le **Frontend** avec :
- Type de source (WFS, CSV, SHP, etc.)
- URL de la source

Puis il demande le chargement de la source.

### 2. Processus d'ingestion 

Le **Backend** reçoit la requête d'ingestion et exécute les étapes suivantes :
  - Génère un `dag_run_id` (uuid) et un `staging_table_name`
  - Création d'un `integrity_link`.
  - Génère une backend callback URL pour la fin du DAG (si succès)
    - Pour mettre à jour l'`integrity_link` avec :
      - `staging_table_name` (généré côté Backend)
      - `staging_retrieve_time` (diff entre le temps de création de l'`integrity_link` et la reception de la callback)
      - `integrity_owner` (fournis par le backend via l'authentification)
      - `integrity_organization` (fournis par le backend via l'authentification)
  - Génère une backend callback URL pour la fin du DAG (si échec)
    - TODO: définir ce qu'on fait en cas d'échec
  - Déclenche le DAG `staging_dag` via l'API Airflow avec les paramètres suivants :
    - `dag_run_id`
    - `source_type`
    - `source_url`
    - `callback_success_url`
    - `callback_failure_url`
  - Retourne le `dag_id`, `dag_run_id` et `integrity_link_id` au **Frontend** pour le suivi du statut du DAG.

### 3. Monitoring du statut du DAG

Le **Frontend** poll régulièrement le **Backend** pour obtenir le statut du DAG en cours d'exécution.
Le **Backend** interroge l'API Airflow pour obtenir le statut du DAG (`queued`, `running`, `success`, `failed`) et le retourne au **Frontend**.

TODO: quid de la gestion d'erreur ?

### 4. Exécution du DAG de staging côté Airflow

Le `staging_dag` est trigger :
- Download, lecture et ingestion dans une table staging PostgreSQL selon le type de source
  - Utilise la lib `data_manipulation` pour cela
- Appel de la **Backend** callback correcte, suivant si le DAG a réussi ou échoué

### 5. Prévisualisation des données et transformations en local

Le **Frontend** est notifié que le `staging_dag` a réussi via le polling.

On passe à la 2ème étape du tunnel d'ingestion.
Le **Frontend** demande au **Backend** un aperçu des données ingérées dans la table staging.
Le **Backend** query la table staging et retourne un échantillon des données, le schéma et les métadonnées associées.
L'utilisateur peut visualiser ce subset et y appliquer des transformations via des paramètres de transformation dans la query :
- Filtrage de colonnes
- Renommage de colonnes
- Projection spatiale

+

Une 3eme étape de récurrence (CRON) de mise à jour peut être configurée (si ce n'est pas un fichier local).

TODO: à définir plus précisément.

### 6. Configuration finale

L'utilisateur valide la configuration finale dans le **Frontend** en l'envoit au **Backend** :
- Le titre (qui sera sanitisé par le backend pour devenir le nom de la table finale)
- La config de transformation (renommage, filtrage, projection, etc...)
- Optionnel: Le schedule (si applicable = si pas un fichier local)

Le **Backend** reçoit cette configuration et exécute les étapes suivantes :
- Sanitisation du titre pour créer le nom de la table finale + renseigner l'info brute dans l'integrityLink (`integrity_title`)
- Créé le layer (via geoserver) + renseigner cette info dans l'integrityLink (`data_id`)
- Créé la fiche de metadonnée (via geonetwork) et la lier au layer geoserver + renseigner cette info dans l'integrityLink (`metadata_id`)
- Si fournis et applicable, renseigne le schedule de mise à jour dans l'integrityLink (`schedule` et `schedule_enabled`)
- Renseigne la config json de transformation dans l'integrityLink (`integrity_transformation`)
- Génère une backend callback URL pour la fin du DAG (si succès) :
  - Met à jour l'`integrity_link` avec :
    - `final_table_name` (généré côté Backend = le nom sanitisé et unique)
    - `last_retrieval_timestamp` (requête à airflow sur le dag_run_id pour connaitre le temps d'exécution)
- Génère une backend callback URL pour la fin du DAG (si échec)
  - TODO: définir ce qu'on fait en cas d'échec
- Met à jour l'`integrity_link` en avance avec :
  - `integrity_title`
  - `integrity_transformation`
- Déclenche le `process_dag` via l'API Airflow avec les paramètres suivants :
  - `staging_table_name` (récupéré depuis l'integrity_link)
  - `final_table_name` (le titre brut sanitisé et unique)
  - `callback_success_url`
  - `callback_failure_url`
- Retourne le `dag_id`, `dag_run_id` et `integrity_link_id` au **Frontend** pour le suivi du statut du DAG.

### 7. Transformation finale via le DAG de transformation Airflow

TODO: à détailler. pour l'instant, on reprends juste les tasks du `staging_dag` en les adaptant pour écrire dans la table finale.

### 8. Ingestions récurrentes
- Airflow poll régulièrement la BDD pour détecter les `integrity_link` avec `schedule_enabled = true`
- Création dynamique de DAGs pour chaqu'un de ces `integrity_link`
- Exécution des DAGs de transformation pour mettre à jour les données finales selon le schedule défini


## Notes additionnelles

- Il faut penser à gérer les droits
- Il faut penser à la gestion des erreurs
- Les callbacks du backend doivent être sécurisées (pas possible de les appeler depuis l'extérieur d'Airflow)
- Il faut penser à clear les tables staging quand elles ne sont plus utilisées
