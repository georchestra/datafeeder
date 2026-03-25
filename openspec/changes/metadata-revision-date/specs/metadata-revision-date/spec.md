## ADDED Requirements

### Requirement: Date de révision à la création initiale de la fiche
Le système DOIT définir la date de révision dans la fiche de métadonnées lors de la première ingestion. La date de révision DOIT être égale à la date de création du jeu de données. Elle DOIT être présente à deux niveaux : au niveau métadonnée (`mdb:dateInfo`) et au niveau citation (`cit:CI_Citation/cit:date`).

#### Scenario: Première ingestion avec création de fiche
- **WHEN** un utilisateur lance l'ingestion d'un nouveau jeu de données via le tunnel d'ingestion
- **THEN** la fiche de métadonnées générée contient une `mdb:dateInfo` avec `codeListValue="revision"` dont la valeur est la date de création du jeu de données
- **AND** la citation (`mri:citation/cit:CI_Citation`) contient un élément `cit:date` avec `codeListValue="revision"` dont la valeur est la date de création du jeu de données

#### Scenario: Vérification du format de la date de révision initiale
- **WHEN** la fiche de métadonnées est générée lors de la première ingestion
- **THEN** la date de révision au niveau `mdb:dateInfo` est au format `YYYY-MM-DDTHH:MM:SS` dans un élément `gco:DateTime`
- **AND** la date de révision au niveau citation est au format `YYYY-MM-DD` dans un élément `gco:Date`

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

### Requirement: Support des schémas ISO 19115-3 et ISO 19139
Le système DOIT supporter la mise à jour de la date de révision pour les fiches de métadonnées au format ISO 19115-3 et ISO 19139.

#### Scenario: Mise à jour d'une fiche ISO 19115-3
- **WHEN** la fiche de métadonnées existante est au format ISO 19115-3 (namespace racine `http://standards.iso.org/iso/19115/-3/mdb/2.0`)
- **THEN** le système localise la date de révision via les XPath ISO 19115-3 (`mdb:dateInfo/cit:CI_Date` avec `codeListValue="revision"` et `mri:citation/cit:CI_Citation/cit:date/cit:CI_Date` avec `codeListValue="revision"`)
- **AND** met à jour ou insère l'élément de date de révision

#### Scenario: Mise à jour d'une fiche ISO 19139
- **WHEN** la fiche de métadonnées existante est au format ISO 19139 (namespace racine `http://www.isotc211.org/2005/gmd`)
- **THEN** le système localise la date de révision via les XPath ISO 19139 (`gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date` avec `codeListValue="revision"`)
- **AND** met à jour ou insère l'élément de date de révision

#### Scenario: Schéma non supporté
- **WHEN** la fiche de métadonnées existante n'est ni au format ISO 19115-3 ni au format ISO 19139
- **THEN** le système journalise un avertissement indiquant le schéma non supporté
- **AND** la mise à jour de la date de révision est ignorée sans erreur
