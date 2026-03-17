## ADDED Requirements

### Requirement: Liste configurable de fréquences de récurrence

Le système DOIT exposer une liste de fréquences de récurrence autorisées, configurable via les paramètres applicatifs. Chaque fréquence est un code au format `<quantité><unité>` où l'unité est l'une de : `m` (minute), `h` (heure), `d` (jour), `w` (semaine), `M` (mois), `y` (année). Une seule valeur est acceptée à la fois (ex : `2M` est valide, `1d 5m` NE DOIT PAS être accepté).

La liste par défaut DOIT être : `1m`, `1h`, `1d`, `1w`, `1M`, `1y`.

#### Scenario: Récupération de la liste des fréquences via l'API settings

- **WHEN** le frontend appelle l'endpoint GET /api/v1/settings
- **THEN** la réponse DOIT contenir un champ `recurrence_frequencies` avec la liste des codes de fréquences autorisés (ex : `["1m","1h","1d","1w","1M","1y"]`)

#### Scenario: La liste est configurable par variable d'environnement

- **WHEN** la variable d'environnement `RECURRENCE_FREQUENCIES` est définie à `'["1h","1d","1M"]'`
- **THEN** l'endpoint settings DOIT retourner uniquement `["1h","1d","1M"]`

#### Scenario: Validation d'une fréquence invalide

- **WHEN** un utilisateur soumet une fréquence `1d 5m` (valeur composée)
- **THEN** le backend DOIT rejeter la requête avec une erreur de validation HTTP 422

#### Scenario: Validation d'une fréquence hors liste

- **WHEN** un utilisateur soumet une fréquence `3h` qui n'est pas dans la liste configurée `["1h","1d","1M"]`
- **THEN** le backend DOIT rejeter la requête avec une erreur de validation HTTP 422

---

### Requirement: Conversion de fréquence en expression cron

Le système DOIT convertir un code de fréquence en une expression cron valide pour Airflow. Les règles de conversion sont :

- Pour les fréquences en minutes (`m`) : `*/<n> * * * *`
- Pour les fréquences en heures (`h`) : `0 */<n> * * *`
- Pour les fréquences en jours (`d`) ou plus : l'exécution DOIT être planifiée à l'heure nocturne configurable (`RECURRENCE_EXECUTION_HOUR`, défaut : 4h)
- Pour les fréquences en mois (`M`) ou en années (`y`) : le jour d'ancrage DOIT être le jour courant au moment de la soumission
- Pour les Semaines (`w`) : conversion en jours (`n * 7`)

#### Scenario: Conversion d'une fréquence journalière

- **WHEN** la fréquence est `1d` et `RECURRENCE_EXECUTION_HOUR` vaut `4`
- **THEN** l'expression cron générée DOIT être `0 4 */1 * *`

#### Scenario: Conversion d'une fréquence mensuelle avec ancrage au jour courant

- **WHEN** la fréquence est `1M`, `RECURRENCE_EXECUTION_HOUR` vaut `4`, et la date courante est le 27 février
- **THEN** l'expression cron générée DOIT être `0 4 27 */1 *`

#### Scenario: Gestion du 29 février

- **WHEN** la fréquence est `1M`, et la date courante est le 29 février (année bissextile)
- **THEN** le jour d'ancrage DOIT être plafonné à 28, et l'expression cron générée DOIT être `0 4 28 */1 *`

#### Scenario: Conversion d'une fréquence en minutes

- **WHEN** la fréquence est `1m`
- **THEN** l'expression cron générée DOIT être `*/1 * * * *`

#### Scenario: Conversion d'une fréquence hebdomadaire

- **WHEN** la fréquence est `1w` et `RECURRENCE_EXECUTION_HOUR` vaut `4`
- **THEN** l'expression cron générée DOIT être `0 4 */7 * *`

#### Scenario: Conversion d'une fréquence annuelle

- **WHEN** la fréquence est `1y`, `RECURRENCE_EXECUTION_HOUR` vaut `4`, et la date courante est le 15 mars
- **THEN** l'expression cron générée DOIT être `0 4 15 */12 *`

---

### Requirement: Persistance de la récurrence lors du processus d'ingestion

Le système DOIT permettre de définir optionnellement une fréquence de récurrence lors de la finalisation de l'ingestion (étape process). Si une fréquence est fournie, le cron calculé est enregistré dans `IntegrityLink.schedule` et `schedule_enabled` est mis à `true`.

#### Scenario: Soumission du process avec récurrence

- **WHEN** l'utilisateur soumet le formulaire de process avec `recurrence_frequency: "1d"`
- **THEN** le champ `schedule` de l'IntegrityLink DOIT contenir l'expression cron correspondante (ex : `0 4 */1 * *`) et `schedule_enabled` DOIT être `true`

#### Scenario: Soumission du process sans récurrence

- **WHEN** l'utilisateur soumet le formulaire de process sans fournir de `recurrence_frequency` (null)
- **THEN** les champs `schedule` et `schedule_enabled` de l'IntegrityLink NE DOIVENT PAS être modifiés (restent à `null` et `false`)

#### Scenario: Heure d'exécution nocturne configurable

- **WHEN** la variable `RECURRENCE_EXECUTION_HOUR` est configurée à `3`
- **THEN** les expressions cron générées pour les fréquences journalières et supérieures DOIVENT utiliser l'heure `3` (ex : `1d` → `0 3 */1 * *`)

---

### Requirement: Sélecteur de récurrence dans le tunnel d'ingestion (étape 2)

Le tunnel d'ingestion DOIT afficher un sélecteur de récurrence sur l'étape 2 (configuration), uniquement pour les sources distantes (toutes sauf fichier local). Le sélecteur DOIT être un champ déroulant présentant les fréquences autorisées récupérées depuis le backend.

#### Scenario: Affichage du sélecteur pour une source distante

- **WHEN** l'utilisateur est à l'étape 2 du tunnel avec une source de type URL, FTP, API ou database
- **THEN** un sélecteur de récurrence DOIT être visible avec les fréquences disponibles, et une option vide par défaut (pas de récurrence)

#### Scenario: Masquage du sélecteur pour un fichier local

- **WHEN** l'utilisateur est à l'étape 2 du tunnel avec une source de type fichier local
- **THEN** le sélecteur de récurrence NE DOIT PAS être affiché

#### Scenario: Sélection par défaut

- **WHEN** le sélecteur de récurrence est affiché
- **THEN** la valeur par défaut DOIT être vide (aucune récurrence — ingestion one-shot)

---

### Requirement: Désactivation des fréquences inférieures au temps de récupération

Les fréquences dont la période est inférieure au temps de récupération mesuré du jeu de données (`staging_retrieve_time`) DOIVENT être grisées et non sélectionnables dans le sélecteur.

#### Scenario: Fréquence grisée car inférieure au temps de récupération

- **WHEN** le `staging_retrieve_time` du jeu de données est de 2 heures et les fréquences disponibles sont `["1m","1h","1d","1w","1M","1y"]`
- **THEN** les options `1m` et `1h` DOIVENT être grisées et non sélectionnables

#### Scenario: Infobulle explicative sur une fréquence grisée

- **WHEN** l'utilisateur survole une fréquence grisée
- **THEN** une infobulle DOIT expliquer que cette fréquence est inférieure au temps de récupération de la donnée

#### Scenario: Pas de staging_retrieve_time disponible

- **WHEN** le `staging_retrieve_time` est null (non mesuré)
- **THEN** toutes les fréquences DOIVENT être activées et sélectionnables

---

### Requirement: Agrandissement de la colonne schedule en base

Le champ `schedule` de la table `integrity_link` DOIT supporter des expressions cron de longueur suffisante. La contrainte `max_length` DOIT être augmentée de 10 à 20 caractères pour accommoder les expressions cron les plus longues.

#### Scenario: Migration de la colonne schedule

- **WHEN** la migration est appliquée
- **THEN** la colonne `schedule` de `datakern.integrity_link` DOIT être de type `VARCHAR(20)`
