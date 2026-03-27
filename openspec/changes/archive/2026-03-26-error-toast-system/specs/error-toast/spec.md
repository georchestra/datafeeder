## ADDED Requirements

### Requirement: Affichage d'un message d'erreur persistant lors de l'échec d'une opération

Le système SHALL afficher un toast d'erreur lorsqu'une des opérations suivantes échoue : sauvegarde des métadonnées, (dé)publication GeoNetwork/GeoServer, édition des droits GeoNetwork/GeoServer, édition de la récurrence, suppression d'un dataset.

#### Scenario: Échec d'une opération déclenchée par un bouton

- **WHEN** l'utilisateur clique sur un bouton déclenchant une opération et que cette opération retourne une erreur
- **THEN** un toast d'erreur est affiché avec le nom de l'opération dans le message (ex. "La sauvegarde des métadonnées a rencontré une erreur")
- **THEN** le bouton déclencheur redevient interactif

#### Scenario: Affichage du toast avec les éléments visuels attendus

- **WHEN** un toast d'erreur est affiché
- **THEN** le toast contient une icône triangle d'avertissement
- **THEN** le toast contient le message d'erreur incluant le nom de l'opération
- **THEN** le toast contient un bouton de fermeture (×)

### Requirement: Persistance du toast lors de la navigation

Le toast d'erreur SHALL rester affiché même si l'utilisateur navigue vers une autre page, jusqu'à ce qu'il le ferme explicitement.

#### Scenario: Navigation après l'apparition d'un toast

- **WHEN** un toast d'erreur est affiché
- **WHEN** l'utilisateur navigue vers une autre route
- **THEN** le toast reste visible

#### Scenario: Fermeture manuelle du toast

- **WHEN** un toast d'erreur est affiché
- **WHEN** l'utilisateur clique sur le bouton de fermeture du toast
- **THEN** le toast disparaît

### Requirement: Positionnement du toast dans la zone applicative

Le toast d'erreur SHALL être positionné à l'intérieur du conteneur de l'application, indépendamment de tout en-tête injecté au-dessus de la racine de l'application (par ex. l'en-tête geOrchestra).

#### Scenario: Toast visible dans la zone applicative avec en-tête externe

- **GIVEN** l'application est déployée dans un contexte où un en-tête externe (geOrchestra) est injecté au-dessus de `<app-root>`
- **WHEN** un toast d'erreur est affiché
- **THEN** le toast est visible à l'intérieur de la zone applicative, sans chevaucher l'en-tête externe

### Requirement: Empilement des toasts multiples

Si plusieurs erreurs surviennent, les toasts SHALL s'empiler, le toast le plus récent apparaissant en bas de la liste.

#### Scenario: Deux erreurs successives

- **WHEN** une première opération échoue et un toast est affiché
- **WHEN** une deuxième opération échoue avant que l'utilisateur ne ferme le premier toast
- **THEN** deux toasts sont visibles simultanément
- **THEN** le toast correspondant à la deuxième erreur est positionné en dessous du premier

#### Scenario: Fermeture individuelle d'un toast dans une pile

- **WHEN** plusieurs toasts sont affichés
- **WHEN** l'utilisateur ferme l'un d'eux
- **THEN** seul ce toast disparaît
- **THEN** les autres toasts restent affichés
