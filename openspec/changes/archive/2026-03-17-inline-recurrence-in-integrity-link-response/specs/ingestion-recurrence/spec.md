## ADDED Requirements

### Requirement: Exposition de la récurrence dans la réponse IntegrityLink

La réponse de `GET /ingestion/integrity-link/{id}` DOIT inclure les champs `preset_id` en plus du champ `schedule` déjà présent, permettant aux consommateurs d'obtenir cron et preset en un seul appel.

#### Scenario: Récupération d'un IntegrityLink avec une récurrence configurée

- **WHEN** l'API reçoit `GET /ingestion/integrity-link/{id}` pour un IntegrityLink dont `schedule` est `"0 4 * * *"`
- **THEN** la réponse DOIT contenir `schedule: "0 4 * * *"` et `preset_id: "EVERY_DAY"`

#### Scenario: Récupération d'un IntegrityLink sans récurrence

- **WHEN** l'API reçoit `GET /ingestion/integrity-link/{id}` pour un IntegrityLink dont `schedule` est `null`
- **THEN** la réponse DOIT contenir `schedule: null` et `preset_id: null`

#### Scenario: Récupération d'un IntegrityLink avec un cron personnalisé non mappé à un preset

- **WHEN** l'API reçoit `GET /ingestion/integrity-link/{id}` pour un IntegrityLink dont `schedule` est une expression cron ne correspondant à aucun preset connu
- **THEN** la réponse DOIT contenir le `schedule` renseigné et `preset_id: null`

## REMOVED Requirements

### Requirement: Endpoint dédié de lecture de la récurrence d'un IntegrityLink

**Reason**: L'endpoint `GET /ingestion/integrity-link/{id}/recurrence` dupliquait des données déjà disponibles sur `IntegrityLink.schedule`. Les champs `cron` et `preset_id` sont désormais exposés directement dans `IntegrityLinkResponse`.

**Migration**: Utiliser `GET /ingestion/integrity-link/{id}` et lire les champs `schedule` (cron) et `preset_id` depuis la réponse.
