## ADDED Requirements

### Requirement: Modal de confirmation pour actions destructives

Le système SHALL afficher une boîte de dialogue modale de confirmation avant d'exécuter une action destructive (ex. suppression d'un jeu de données). La modale utilise `ConfirmationDialogComponent` de `geonetwork-ui`, ouverte via `MatDialog`.

#### Scenario: Affichage de la modale

- **WHEN** l'utilisateur déclenche une action destructive (ex. clic sur le bouton supprimer)
- **THEN** une modale de confirmation s'affiche par-dessus le contenu, avec un fond semi-transparent bloquant l'interaction avec le reste de l'interface

#### Scenario: Confirmation de l'action

- **WHEN** l'utilisateur clique sur le bouton de confirmation (ex. "Supprimer")
- **THEN** la modale se ferme et l'action destructive est exécutée

#### Scenario: Annulation de l'action

- **WHEN** l'utilisateur clique sur le bouton d'annulation (ex. "Annuler")
- **THEN** la modale se ferme sans exécuter l'action destructive

#### Scenario: Fermeture par la touche Échap

- **WHEN** l'utilisateur appuie sur la touche Échap pendant que la modale est ouverte
- **THEN** la modale se ferme sans exécuter l'action destructive

#### Scenario: Fermeture par clic sur le fond

- **WHEN** l'utilisateur clique sur le fond semi-transparent en dehors de la modale
- **THEN** la modale se ferme sans exécuter l'action destructive

### Requirement: Contenu configurable de la modale

La modale SHALL afficher un titre, un message et des libellés de boutons fournis par l'appelant. Elle ne SHALL PAS contenir de texte en dur.

#### Scenario: Titre et message personnalisés

- **WHEN** la modale est ouverte avec un titre et un message spécifiques
- **THEN** ces textes s'affichent correctement dans la modale

#### Scenario: Libellés de boutons par défaut

- **WHEN** aucun libellé personnalisé n'est fourni
- **THEN** des libellés par défaut sont utilisés ("Confirmer" et "Annuler" ou équivalent en langue active)

### Requirement: Variante visuelle danger

La modale SHALL supporter une variante `danger` qui met en évidence le caractère destructif de l'action via le style du bouton de confirmation (rouge).

#### Scenario: Bouton de confirmation en rouge pour variant danger

- **WHEN** la modale est ouverte avec la variante `danger`
- **THEN** le bouton de confirmation est affiché en rouge (destructive styling)

### Requirement: Accessibilité clavier

La modale SHALL piéger le focus à l'intérieur de la boîte de dialogue tant qu'elle est ouverte, et le restituer à l'élément déclencheur à la fermeture.

#### Scenario: Focus piégé dans la modale

- **WHEN** la modale est ouverte
- **THEN** la navigation clavier (Tab) reste confinée aux éléments interactifs de la modale

#### Scenario: Restauration du focus

- **WHEN** la modale se ferme (confirmation ou annulation)
- **THEN** le focus retourne à l'élément qui a déclenché l'ouverture

### Requirement: Intégration dans le flux de suppression d'un jeu de données

Le composant `integrity-link-list` SHALL utiliser `ConfirmationDialogComponent` de `geonetwork-ui` à la place de `window.confirm()` lors de la suppression d'un jeu de données.

#### Scenario: Suppression confirmée via la modale

- **WHEN** l'utilisateur confirme la suppression via la modale
- **THEN** l'appel API de suppression est effectué et la ligne disparaît de la liste

#### Scenario: Suppression annulée via la modale

- **WHEN** l'utilisateur annule la suppression via la modale
- **THEN** aucun appel API n'est effectué et le jeu de données reste dans la liste
