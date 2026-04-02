## MODIFIED Requirements

### Requirement: Recurrence frequency labels must not expose scheduling details

Le composant d'affichage de la récurrence DOIT afficher :
- Pour un preset connu : le libellé traduit correspondant via les clés i18n (ex : `recurrence.preset.EVERY_DAY`, `recurrence.preset.EVERY_WEEK`, `recurrence.preset.EVERY_MONTH`, etc.)
- Pour un cron personnalisé : la description humaine générée par la bibliothèque cronstrue, localisée selon la langue de l'application
- Pour aucune récurrence : un placeholder traduit via la clé i18n `recurrence.none`

Le système NE DOIT PLUS générer dynamiquement des libellés à partir de codes `<quantité><unité>`.

#### Scenario: Libellé d'un preset en français

- **WHEN** le preset est `EVERY_DAY` et la locale est `fr`
- **THEN** le libellé affiché DOIT être « Tous les jours »

#### Scenario: Libellé d'un preset en anglais

- **WHEN** le preset est `EVERY_WEEK` et la locale est `en`
- **THEN** le libellé affiché DOIT être « Every week »

#### Scenario: Libellé d'un cron personnalisé

- **WHEN** la récurrence est un cron personnalisé `30 2 15 * *` et la locale est `fr`
- **THEN** le libellé affiché DOIT être la description cronstrue en français (ex : « À 02:30, le 15 de chaque mois »)

#### Scenario: Libellé sans récurrence

- **WHEN** aucune récurrence n'est configurée
- **THEN** le libellé affiché DOIT être le placeholder traduit (ex : « Aucune récurrence »)

## REMOVED Requirements

### Requirement: Unknown frequency code falls back to raw code

**Reason**: Les codes de fréquence `<quantité><unité>` n'existent plus. Le fallback pour les crons inconnus est désormais assuré par cronstrue qui fournit une description humaine.

**Migration**: Remplacer le fallback raw-code par un appel cronstrue pour les crons non reconnus comme preset.
