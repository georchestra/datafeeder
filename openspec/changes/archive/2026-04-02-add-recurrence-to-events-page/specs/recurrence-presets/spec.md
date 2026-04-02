## MODIFIED Requirements

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

## RENAMED Requirements

- FROM: `### Requirement: Affichage en lecture seule de la récurrence sur la fiche dataset`
- TO: `### Requirement: Affichage en lecture seule de la récurrence sur la page des événements`
