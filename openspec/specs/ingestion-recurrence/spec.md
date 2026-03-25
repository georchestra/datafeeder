# Capability: Ingestion Recurrence

## Purpose

Defines how recurring ingestion schedules are configured, validated, stored, and displayed during the import wizard. Covers preset-based recurrence selection, cron storage, UI selector behaviour, and database schema requirements.

## Requirements

### Requirement: Persistance de la récurrence lors du processus d'ingestion

Le système DOIT permettre de définir ou d'effacer la récurrence lors de la finalisation de l'ingestion (étape process). Le champ `recurrence` est toujours présent dans la requête (preset ou `null` explicite) — il n'existe pas de distinction entre "non fourni" et "null".

- Si `recurrence` est un preset valide, l'expression cron correspondante est enregistrée dans `IntegrityLink.schedule` et `schedule_enabled` est mis à `true`.
- Si `recurrence` est `null`, `IntegrityLink.schedule` est mis à `null` et `schedule_enabled` est mis à `false`. Cela permet de supprimer une récurrence existante lors d'une re-configuration.

#### Scenario: Soumission du process avec un preset de récurrence

- **WHEN** l'utilisateur soumet le formulaire de process avec `recurrence: "EVERY_DAY"`
- **THEN** le champ `schedule` de l'IntegrityLink DOIT contenir `0 4 * * *` et `schedule_enabled` DOIT être `true`

#### Scenario: Soumission du process avec recurrence null (suppression)

- **WHEN** l'utilisateur soumet le formulaire de process avec `recurrence: null`
- **THEN** les champs `schedule` et `schedule_enabled` de l'IntegrityLink DOIVENT être réinitialisés à `null` et `false`

#### Scenario: Soumission du process avec un preset invalide

- **WHEN** l'utilisateur soumet le formulaire de process avec `recurrence: "INVALID_VALUE"`
- **THEN** le backend DOIT rejeter la requête avec une erreur HTTP 422

---

### Requirement: Sélecteur de récurrence dans le tunnel d'ingestion (étape 2)

Le tunnel d'ingestion DOIT afficher un sélecteur de récurrence sur l'étape 2 (configuration), uniquement pour les sources distantes (toutes sauf fichier local). Le sélecteur DOIT présenter les presets de récurrence définis par le backend.

#### Scenario: Affichage du sélecteur pour une source distante

- **WHEN** l'utilisateur est à l'étape 2 du tunnel avec une source de type URL, FTP, API ou database
- **THEN** un sélecteur de récurrence DOIT être visible avec les presets disponibles, et une option vide par défaut (pas de récurrence)

#### Scenario: Masquage du sélecteur pour un fichier local

- **WHEN** l'utilisateur est à l'étape 2 du tunnel avec une source de type fichier local
- **THEN** le sélecteur de récurrence NE DOIT PAS être affiché

#### Scenario: Sélection par défaut

- **WHEN** le sélecteur de récurrence est affiché
- **THEN** la valeur par défaut DOIT être vide (aucune récurrence — ingestion one-shot)

#### Scenario: Libellés des options du sélecteur

- **WHEN** le sélecteur affiche les presets
- **THEN** chaque option DOIT afficher le libellé traduit du preset (ex : « Chaque minute », « Chaque heure », « Chaque jour », « Chaque semaine », « Chaque mois », « Chaque année »)

---

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

---

### Requirement: Agrandissement de la colonne schedule en base

Le champ `schedule` de la table `integrity_link` DOIT supporter des expressions cron de longueur suffisante. La contrainte `max_length` DOIT être augmentée de 10 à 20 caractères pour accommoder les expressions cron les plus longues.

#### Scenario: Migration de la colonne schedule

- **WHEN** la migration est appliquée
- **THEN** la colonne `schedule` de `datakern.integrity_link` DOIT être de type `VARCHAR(63)`
