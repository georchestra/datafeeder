## ADDED Requirements

### Requirement: Suppression d'un dataset par son propriétaire

Un utilisateur authentifié SHALL pouvoir supprimer un dataset dont il est le propriétaire depuis le tableau de bord de ses données.

#### Scenario: Suppression réussie par le propriétaire

- **WHEN** un utilisateur envoie `DELETE /api/ingestion/integrity-link/{id}` pour un dataset dont il est le propriétaire
- **THEN** le système retourne HTTP 204
- **THEN** le dataset n'est plus accessible via `GET /api/ingestion/integrity-links/`

#### Scenario: Refus de suppression pour un non-propriétaire

- **WHEN** un utilisateur envoie `DELETE /api/ingestion/integrity-link/{id}` pour un dataset dont il n'est pas le propriétaire
- **THEN** le système retourne HTTP 403

#### Scenario: Dataset inexistant

- **WHEN** un utilisateur envoie `DELETE /api/ingestion/integrity-link/{id}` avec un identifiant inconnu
- **THEN** le système retourne HTTP 404

### Requirement: Suppression par un administrateur

Un administrateur SHALL pouvoir supprimer n'importe quel dataset, quel que soit son propriétaire.

#### Scenario: Suppression par un admin d'un dataset appartenant à un autre utilisateur

- **WHEN** un administrateur envoie `DELETE /api/ingestion/integrity-link/{id}` pour un dataset appartenant à un autre utilisateur
- **THEN** le système retourne HTTP 204
- **THEN** le dataset n'est plus accessible

### Requirement: Nettoyage des ressources associées lors de la suppression

Lors de la suppression d'un dataset, le système SHALL nettoyer toutes les ressources associées dans l'ordre suivant : DAG Airflow (si récurrence), couche GeoServer, table de données finale, fiche GeoNetwork, enregistrement IntegrityLink (avec cascade sur IntegrityLinkRule).

#### Scenario: Suppression complète d'un dataset avec récurrence

- **WHEN** un dataset avec un `schedule` défini est supprimé
- **THEN** le DAG Airflow correspondant est supprimé
- **THEN** la couche GeoServer est supprimée
- **THEN** la table de données finale est supprimée
- **THEN** la fiche GeoNetwork est supprimée
- **THEN** l'enregistrement IntegrityLink est supprimé de la base de données
- **THEN** les IntegrityLinkRules associées sont supprimées par cascade

#### Scenario: Suppression d'un dataset sans récurrence

- **WHEN** un dataset sans `schedule` est supprimé
- **THEN** aucune opération Airflow n'est tentée
- **THEN** les autres ressources (GeoServer, table, GeoNetwork, IntegrityLink) sont supprimées

#### Scenario: Ressource GeoServer ou GeoNetwork introuvable

- **WHEN** une ressource GeoServer ou GeoNetwork est introuvable lors de la suppression
- **THEN** l'erreur est ignorée (best-effort) et la suppression se poursuit

### Requirement: Blocage en cas d'échec de suppression du DAG

Si la suppression du DAG Airflow échoue (hors cas 404), le système SHALL retourner une erreur et interrompre le nettoyage.

#### Scenario: Échec de suppression du DAG

- **WHEN** la suppression du DAG Airflow retourne une erreur autre que 404
- **THEN** le backend retourne HTTP 500
- **THEN** aucune autre ressource n'est supprimée
- **THEN** le dataset reste dans la liste

#### Scenario: DAG Airflow introuvable (pas de DAG créé)

- **WHEN** la suppression du DAG retourne 404 (le DAG n'existe pas dans Airflow)
- **THEN** l'erreur est ignorée et le nettoyage se poursuit normalement

### Requirement: Affichage de l'icône de suppression au survol

Dans le tableau de bord des données, l'icône de suppression (corbeille) SHALL apparaître uniquement au survol de la ligne correspondante.

#### Scenario: Survol d'une ligne du tableau

- **WHEN** l'utilisateur survole une ligne du tableau de bord
- **THEN** une icône corbeille apparaît à droite de la ligne

#### Scenario: Fin de survol

- **WHEN** le curseur quitte la ligne
- **THEN** l'icône corbeille disparaît

### Requirement: Disparition du dataset de la liste après suppression

Après une suppression réussie, le dataset SHALL disparaître immédiatement de la liste sans rechargement complet de la page.

#### Scenario: Suppression confirmée par l'utilisateur

- **WHEN** l'utilisateur clique sur l'icône de suppression
- **THEN** une boîte de dialogue de confirmation est affichée
- **WHEN** l'utilisateur confirme la suppression et la requête DELETE retourne HTTP 204
- **THEN** la ligne correspondante est retirée de la liste affichée
- **THEN** la liste restante est inchangée

#### Scenario: Annulation de la suppression par l'utilisateur

- **WHEN** l'utilisateur clique sur l'icône de suppression
- **THEN** une boîte de dialogue de confirmation est affichée
- **WHEN** l'utilisateur annule
- **THEN** aucune requête DELETE n'est envoyée
- **THEN** la ligne reste dans la liste
