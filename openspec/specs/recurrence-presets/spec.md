# Capability: Recurrence Presets

## Purpose

Defines the fixed set of recurrence presets available for scheduling recurring data ingestion, the API endpoints for listing and querying them, and the read-only display on the dataset detail page.

## Requirements

### Requirement: Presets de récurrence fixes

Le système DOIT définir un ensemble fixe de presets de récurrence, chacun associant un identifiant enum à une expression cron. Les presets supportés DOIVENT être :

| Preset         | Expression cron (défaut `RECURRENCE_EXECUTION_HOUR=4`) |
| -------------- | ------------------------------------------------------- |
| `EVERY_MINUTE` | `* * * * *`                                             |
| `EVERY_HOUR`   | `0 * * * *`                                             |
| `EVERY_DAY`    | `0 4 * * *`                                             |
| `EVERY_WEEK`   | `0 4 * * 1`                                             |
| `EVERY_MONTH`  | `0 4 1 * *`                                             |
| `EVERY_YEAR`   | `0 4 1 1 *`                                             |

Les presets `EVERY_DAY`, `EVERY_WEEK`, `EVERY_MONTH` et `EVERY_YEAR` utilisent le paramètre de configuration `RECURRENCE_EXECUTION_HOUR` (défaut : 4) pour l'heure d'exécution. Cet ensemble est codé en dur côté backend. L'ajout d'un nouveau preset nécessite une modification du code source.

#### Scenario: Le backend expose la liste des presets via l'API

- **WHEN** le frontend appelle `GET /ingestion/recurrence-presets`
- **THEN** la réponse DOIT contenir un tableau d'objets `{ "id": "<PRESET_ID>", "cron": "<expression>" }` pour chaque preset défini

#### Scenario: Correspondance preset → cron

- **WHEN** un utilisateur soumet le preset `EVERY_DAY` lors du process
- **THEN** l'expression cron stockée dans `IntegrityLink.schedule` DOIT être `0 4 * * *`

#### Scenario: Preset inconnu rejeté

- **WHEN** un utilisateur soumet un preset `EVERY_TWO_WEEKS` qui n'existe pas dans l'enum
- **THEN** le backend DOIT rejeter la requête avec une erreur HTTP 422

---

### Requirement: preset_id inline sur GET /ingestion/integrity-link/{id}

La réponse de `GET /ingestion/integrity-link/{id}` DOIT inclure un champ `preset_id` (l'identifiant du preset correspondant au `schedule` courant, ou `null`). Ce champ N'EST PAS stocké en base — il est résolu par reverse-lookup dans `CRON_PRESET_MAP` (inverse de `PRESET_CRON_MAP`) à chaque appel.

Il n'existe pas d'endpoint dédié `GET /ingestion/integrity-link/{id}/recurrence`.

#### Scenario: IntegrityLink avec un cron correspondant à un preset connu

- **WHEN** le frontend appelle `GET /ingestion/integrity-link/{id}` pour un IntegrityLink dont le `schedule` vaut `0 4 * * *`
- **THEN** la réponse DOIT contenir `"preset_id": "EVERY_DAY"`

#### Scenario: IntegrityLink avec un cron personnalisé (modifié par un admin)

- **WHEN** le frontend appelle `GET /ingestion/integrity-link/{id}` pour un IntegrityLink dont le `schedule` vaut `30 2 15 * *` (valeur non reconnue dans `CRON_PRESET_MAP`)
- **THEN** la réponse DOIT contenir `"preset_id": null`

#### Scenario: IntegrityLink sans récurrence

- **WHEN** le frontend appelle `GET /ingestion/integrity-link/{id}` pour un IntegrityLink dont le `schedule` est `null`
- **THEN** la réponse DOIT contenir `"preset_id": null`

---

### Requirement: Affichage en lecture seule de la récurrence sur la page des événements

L'interface DOIT afficher la récurrence courante d'un dataset sur la page des événements (`/:intlink_id/events`) dans un combobox désactivé (lecture seule). Le combobox DOIT afficher :
- Le libellé traduit du preset si la valeur correspond à un preset connu
- Une description humaine du cron via cronstrue si la valeur est un cron personnalisé
- « Aucune récurrence » si aucun schedule n'est configuré

#### Scenario: Affichage d'un preset connu sur la page des événements

- **WHEN** l'utilisateur est sur la page des événements d'un dataset dont la récurrence a `preset_id = "EVERY_DAY"` et `cron = "0 4 * * *"`
- **THEN** le combobox DOIT afficher le libellé traduit correspondant (ex : « Tous les jours » en français, « Every day » en anglais)
- **AND** le combobox DOIT être désactivé (non modifiable)

#### Scenario: Affichage d'un cron personnalisé sur la page des événements

- **WHEN** l'utilisateur est sur la page des événements d'un dataset dont la récurrence a `preset_id = null` et `cron = "30 2 15 * *"`
- **THEN** le combobox DOIT afficher la description humaine générée par cronstrue (ex : « À 02:30, le 15 de chaque mois »)
- **AND** le combobox DOIT être désactivé (non modifiable)

#### Scenario: Affichage sans récurrence sur la page des événements

- **WHEN** l'utilisateur est sur la page des événements d'un dataset dont la récurrence a `preset_id = null` et `cron = null`
- **THEN** le combobox DOIT afficher un placeholder traduit (ex : « Aucune récurrence »)
- **AND** le combobox DOIT être désactivé (non modifiable)

#### Scenario: Localisation cronstrue

- **WHEN** la locale de l'application est `fr`
- **THEN** la description cronstrue DOIT être affichée en français
