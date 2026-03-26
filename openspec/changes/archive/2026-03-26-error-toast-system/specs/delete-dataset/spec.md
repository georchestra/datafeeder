## MODIFIED Requirements

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

#### Scenario: Échec de la suppression côté backend

- **WHEN** l'utilisateur confirme la suppression et la requête DELETE retourne une erreur (HTTP 4xx ou 5xx)
- **THEN** un toast d'erreur est affiché avec le message "La suppression a rencontré une erreur"
- **THEN** la ligne reste dans la liste
- **THEN** l'icône de suppression redevient interactive
