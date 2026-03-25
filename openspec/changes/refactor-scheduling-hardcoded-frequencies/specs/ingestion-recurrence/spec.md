## MODIFIED Requirements

### Requirement: Liste configurable de fréquences de récurrence

**Ce requirement est SUPPRIMÉ.** Voir section REMOVED ci-dessous.

---

### Requirement: Conversion de fréquence en expression cron

**Ce requirement est SUPPRIMÉ.** Voir section REMOVED ci-dessous.

---

### Requirement: Persistance de la récurrence lors du processus d'ingestion

Le système DOIT permettre de définir optionnellement une récurrence lors de la finalisation de l'ingestion (étape process). Si un preset de récurrence est fourni, l'expression cron correspondante est enregistrée dans `IntegrityLink.schedule` et `schedule_enabled` est mis à `true`.

#### Scenario: Soumission du process avec un preset de récurrence

- **WHEN** l'utilisateur soumet le formulaire de process avec `recurrence: "EVERY_DAY"`
- **THEN** le champ `schedule` de l'IntegrityLink DOIT contenir `0 4 * * *` et `schedule_enabled` DOIT être `true`

#### Scenario: Soumission du process sans récurrence

- **WHEN** l'utilisateur soumet le formulaire de process sans fournir de `recurrence` (null)
- **THEN** les champs `schedule` et `schedule_enabled` de l'IntegrityLink NE DOIVENT PAS être modifiés (restent à `null` et `false`)

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

## REMOVED Requirements

### Requirement: Liste configurable de fréquences de récurrence

**Reason**: Le système ne nécessite plus une liste configurable de fréquences. Les presets sont désormais codés en dur dans le backend. La flexibilité n'est pas requise et ajoutait de la complexité inutile.

**Migration**: Supprimer la variable d'environnement `RECURRENCE_FREQUENCIES`. `RECURRENCE_EXECUTION_HOUR` est conservé comme paramètre de configuration pour l'heure d'exécution des presets quotidiens et supérieurs (défaut : 4). Les administrateurs qui avaient personnalisé la liste de fréquences doivent utiliser les presets définis ou modifier le cron directement en base.

---

### Requirement: Conversion de fréquence en expression cron

**Reason**: Le service de conversion `<quantité><unité>` → cron est remplacé par un mapping direct preset → cron. Plus besoin de parser des codes de fréquence ni de gérer les cas limites (29 février, ancrage jour courant, etc.).

**Migration**: Supprimer `recurrence_service.py` et ses tests. Le mapping est désormais une simple correspondance enum → string.

---

### Requirement: Désactivation des fréquences inférieures au temps de récupération

**Reason**: Avec un ensemble fixe de presets (minute, heure, jour, semaine, mois, année), le mécanisme de filtrage basé sur le temps de récupération n'est plus nécessaire. Le choix du preset approprié est laissé à l'utilisateur.

**Migration**: Supprimer la logique `FREQUENCY_MIN_SECONDS` et le filtrage basé sur `staging_retrieve_time` dans le composant frontend.
