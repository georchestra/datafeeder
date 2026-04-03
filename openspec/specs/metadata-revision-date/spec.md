# Specification: metadata-revision-date

## Purpose

Define how the system manages dataset metadata dates (creation and revision) in GeoNetwork throughout the ingestion lifecycle: initial ingestion, recurrent ingestion, and reconfiguration.

## Requirements

### Requirement: Date de création correcte à la création initiale de la fiche
Le système DOIT définir correctement la date de création (`mdb:dateInfo` avec `codeListValue="creation"`) dans la fiche de métadonnées lors de la première ingestion. La date de création DOIT correspondre à la date de création du jeu de données. Le template XML NE DOIT PAS contenir de date de révision à la création initiale.

#### Scenario: Première ingestion avec date de création correcte
- **WHEN** un utilisateur lance l'ingestion d'un nouveau jeu de données via le tunnel d'ingestion
- **THEN** la fiche de métadonnées générée contient une `mdb:dateInfo` avec `codeListValue="creation"` dont la valeur correspond à la date de création du jeu de données
- **AND** la fiche NE contient PAS de `mdb:dateInfo` avec `codeListValue="revision"`

#### Scenario: Format de la date de création
- **WHEN** la fiche de métadonnées est générée lors de la première ingestion
- **THEN** la date de création au niveau `mdb:dateInfo` est au format `YYYY-MM-DDTHH:MM:SSZ` dans un élément `gco:DateTime`

### Requirement: Mise à jour de la date de révision sur récurrence
Le système DOIT mettre à jour la date de révision dans la fiche de métadonnées GeoNetwork après chaque exécution réussie d'une ingestion récurrente. Si une date de révision existe déjà, elle DOIT être remplacée. Si elle n'existe pas encore, elle DOIT être ajoutée.

#### Scenario: Récurrence réussie avec date de révision existante
- **WHEN** une ingestion récurrente se termine avec succès
- **AND** la fiche de métadonnées contient déjà une date de révision
- **THEN** la date de révision existante est remplacée par la date et l'heure courantes (UTC)

#### Scenario: Récurrence réussie sans date de révision existante
- **WHEN** une ingestion récurrente se termine avec succès
- **AND** la fiche de métadonnées ne contient pas de date de révision (uniquement création et/ou publication)
- **THEN** une date de révision est ajoutée à la liste des dates avec la date et l'heure courantes (UTC)

#### Scenario: URL de callback correcte dans le générateur de DAGs planifiés
- **WHEN** le générateur de DAGs planifiés (`process-dag-generator.py`) crée un DAG de récurrence pour un `IntegrityLink`
- **THEN** l'URL de callback de succès est construite à partir de la variable d'environnement `BACKEND_URL` et pointe vers l'endpoint `/ingestion/process/dag_success`
- **AND** l'URL de callback d'échec pointe vers l'endpoint `/ingestion/process/dag_failure`
- **AND** les paramètres `integrity_link_id` et `final_table_name` sont inclus dans les URLs de callback en tant que query parameters

#### Scenario: Échec de la mise à jour de la date de révision
- **WHEN** une ingestion récurrente se termine avec succès
- **AND** la mise à jour de la date de révision dans GeoNetwork échoue (ex. : GeoNetwork indisponible)
- **THEN** le système journalise un avertissement
- **AND** le succès de l'ingestion N'EST PAS remis en cause

### Requirement: Mise à jour de la date de révision sur reconfiguration
Le système DOIT mettre à jour la date de révision dans la fiche de métadonnées GeoNetwork après une reconfiguration réussie d'un jeu de données. La reconfiguration correspond à un passage dans le tunnel d'ingestion pour un jeu de données dont la fiche existe déjà.

#### Scenario: Reconfiguration réussie d'un jeu de données existant
- **WHEN** un utilisateur reconfigure un jeu de données existant via le tunnel d'ingestion
- **AND** le traitement se termine avec succès
- **THEN** la date de révision dans la fiche de métadonnées est mise à jour avec la date et l'heure courantes (UTC)

### Requirement: Sauvegarde sans modification du statut de publication
La mise à jour de la date de révision DOIT utiliser `POST /records` avec `uuidProcessing=OVERWRITE` et NON la republication. Le statut de publication de la fiche NE DOIT PAS être modifié par la mise à jour de la date de révision.

**Note**: GeoNetwork met systématiquement à jour `mdb:dateInfo[revision]` (date de la fiche) lors de toute sauvegarde via `POST /records`, en raison du schema plugin `update-fixed-info.xsl`. Ce comportement ne peut pas être désactivé via l'API (`updateDateStamp` n'est supporté que par `PUT /records/batchediting`, pas par `POST /records`). Ce comportement est accepté.

#### Scenario: Sauvegarde préservant le statut publié
- **WHEN** une fiche de métadonnées publiée reçoit une mise à jour de date de révision
- **THEN** le système appelle `POST /records` avec `uuidProcessing=OVERWRITE`
- **AND** le statut de publication de la fiche reste inchangé (publiée)

#### Scenario: Sauvegarde préservant le statut non publié
- **WHEN** une fiche de métadonnées non publiée reçoit une mise à jour de date de révision
- **THEN** le système appelle `POST /records` avec `uuidProcessing=OVERWRITE`
- **AND** le statut de publication de la fiche reste inchangé (non publiée)

### Requirement: Support des schémas ISO 19115-3 et ISO 19139
Le système DOIT supporter la mise à jour de la date de révision du **jeu de données** pour les fiches au format ISO 19115-3 et ISO 19139. Seuls les éléments de date au niveau de la citation (`mri:citation` en 19115-3, `gmd:CI_Citation` en 19139) DOIVENT être modifiés par le système. Les éléments de date portant sur la fiche de métadonnées elle-même (`mdb:dateInfo` en 19115-3, `gmd:dateStamp` en 19139) NE DOIVENT PAS être modifiés par le code Python — GeoNetwork les met à jour automatiquement lors de la sauvegarde (comportement accepté).

#### Scenario: Mise à jour d'une fiche ISO 19115-3
- **WHEN** la fiche de métadonnées existante est au format ISO 19115-3 (namespace racine `http://standards.iso.org/iso/19115/-3/mdb/2.0`)
- **THEN** le système localise la date de révision du jeu de données via le XPath `mri:citation/cit:CI_Citation/cit:date/cit:CI_Date` avec `codeListValue="revision"`, en cherchant un sous-élément `gco:DateTime` ou `gco:Date`
- **AND** si un élément `gco:DateTime` ou `gco:Date` est trouvé, il est remplacé par un `gco:DateTime` au format `YYYY-MM-DDTHH:MM:SSZ`
- **AND** si aucun `cit:CI_Date[revision]` n'existe, un nouvel élément est inséré avec un `gco:DateTime` au format `YYYY-MM-DDTHH:MM:SSZ`
- **AND** le code Python ne modifie pas `mdb:dateInfo` (date de la fiche)

#### Scenario: Mise à jour d'une fiche ISO 19139
- **WHEN** la fiche de métadonnées existante est au format ISO 19139 (namespace racine `http://www.isotc211.org/2005/gmd`)
- **THEN** le système localise la date de révision du jeu de données via le XPath `gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date` avec `codeListValue="revision"`, en cherchant un sous-élément `gco:DateTime` ou `gco:Date`
- **AND** si un élément `gco:DateTime` ou `gco:Date` est trouvé, il est remplacé par un `gco:DateTime` au format `YYYY-MM-DDTHH:MM:SSZ`
- **AND** si aucun `gmd:CI_Date[revision]` n'existe, un nouvel élément est inséré avec un `gco:DateTime` au format `YYYY-MM-DDTHH:MM:SSZ`
- **AND** le code Python ne modifie pas `gmd:dateStamp` (date de la fiche)

#### Scenario: Schéma non supporté
- **WHEN** la fiche de métadonnées existante n'est ni au format ISO 19115-3 ni au format ISO 19139
- **THEN** le système journalise un avertissement indiquant le schéma non supporté
- **AND** la mise à jour de la date de révision est ignorée sans erreur
