## ADDED Requirements

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

### Requirement: Endpoint de récurrence d'un IntegrityLink

Le système DOIT exposer un endpoint `GET /ingestion/integrity-link/{id}/recurrence` retournant la récurrence actuellement configurée pour un IntegrityLink donné. La réponse DOIT contenir deux champs : `cron` (l'expression cron stockée en base) et `preset_id` (l'identifiant du preset correspondant, ou `null`). Le `preset_id` N'EST PAS stocké en base — il est résolu par reverse-lookup dans `CRON_PRESET_MAP` (inverse de `PRESET_CRON_MAP`) à chaque appel.

#### Scenario: IntegrityLink avec un cron correspondant à un preset connu

- **WHEN** le frontend appelle `GET /ingestion/integrity-link/{id}/recurrence` pour un IntegrityLink dont le `schedule` vaut `0 4 * * *`
- **THEN** la réponse DOIT être `{ "preset_id": "EVERY_DAY", "cron": "0 4 * * *" }`

#### Scenario: IntegrityLink avec un cron personnalisé (modifié par un admin)

- **WHEN** le frontend appelle `GET /ingestion/integrity-link/{id}/recurrence` pour un IntegrityLink dont le `schedule` vaut `30 2 15 * *` (valeur non reconnue dans `CRON_PRESET_MAP`)
- **THEN** la réponse DOIT être `{ "preset_id": null, "cron": "30 2 15 * *" }`

#### Scenario: IntegrityLink sans récurrence

- **WHEN** le frontend appelle `GET /ingestion/integrity-link/{id}/recurrence` pour un IntegrityLink dont le `schedule` est `null`
- **THEN** la réponse DOIT être `{ "preset_id": null, "cron": null }`

#### Scenario: IntegrityLink inexistant

- **WHEN** le frontend appelle `GET /ingestion/integrity-link/{id}/recurrence` avec un id inexistant
- **THEN** le backend DOIT retourner HTTP 404

---

### Requirement: Affichage en lecture seule de la récurrence sur la fiche dataset

L'interface DOIT afficher la récurrence courante d'un dataset sur sa page de détail dans un combobox désactivé (lecture seule). Le combobox DOIT afficher :
- Le libellé traduit du preset si la valeur correspond à un preset connu
- Une description humaine du cron via cronstrue si la valeur est un cron personnalisé
- « Aucune récurrence » si aucun schedule n'est configuré

#### Scenario: Affichage d'un preset connu

- **WHEN** la récurrence d'un IntegrityLink a `preset_id = "EVERY_DAY"` et `cron = "0 4 * * *"`
- **THEN** le combobox DOIT afficher le libellé traduit correspondant (ex : « Tous les jours » en français, « Every day » en anglais)
- **AND** le combobox DOIT être désactivé (non modifiable)

#### Scenario: Affichage d'un cron personnalisé

- **WHEN** la récurrence d'un IntegrityLink a `preset_id = null` et `cron = "30 2 15 * *"`
- **THEN** le combobox DOIT afficher la description humaine générée par cronstrue (ex : « À 02:30, le 15 de chaque mois »)
- **AND** le combobox DOIT être désactivé (non modifiable)

#### Scenario: Affichage sans récurrence

- **WHEN** la récurrence d'un IntegrityLink a `preset_id = null` et `cron = null`
- **THEN** le combobox DOIT afficher un placeholder traduit (ex : « Aucune récurrence »)
- **AND** le combobox DOIT être désactivé (non modifiable)

#### Scenario: Localisation cronstrue

- **WHEN** la locale de l'application est `fr`
- **THEN** la description cronstrue DOIT être affichée en français
