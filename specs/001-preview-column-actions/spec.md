# Feature Specification: Actions sur les colonnes de l'aperçu tabulaire

**Feature Branch**: `001-preview-column-actions`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: "Dans le tunnel d'ingestion, à l'étape de configuration du jeu de données, l'utilisateur a un aperçu tabulaire du jeu de données. L'utilisateur peux agir directement depuis la visualisation de l'aperçu pour transformer le modèle de la donnée. Pour chaque colonne, il peut choisir parmi les actions suivantes : retirer, renommer, changer le type, appliquer un filtre. Les actions sont affichées en cliquant sur un bouton dans l'entête de la colonne, qui fait apparaître une liste des actions disponibles. Seul l'action pour renommer la colonne est disponible en dehors du menu, en éditant directement le nom de la colonne là où il est affiché. Retirer une colonne la garde visible mais grisée, aucune autre action n'est plus disponible dessus, l'icône du menu des actions dans l'entête change pour devenir une icône de restauration de la colonne. Changer le type affiche une liste de types prédéfinis : booléen, numéric, texte, date. Filtrer la colonne ne peut se faire qu'avec les opérateurs suivants : exactement, contient, commence par. Un seul filtre par colonne est applicable en même temps. La saisie d'un nouveau filtre sur une colonne déjà filtrée vient remplacer le filtre précédent. Les filtres sur différentes colonnes se cumulent. Lorsqu'une action est configurée sur une colonne, un indicateur visuel est positionné sur le bouton qui permet d'ouvrir le menu des actions, et sur la ligne dans la liste des actions. Le configuration de la transformation est appliquée directement à chaque modification de l'utilisateur, avec un debounce dans le cas des saisie texte. Le frontend demande alors un nouvel aperçu au backend avec les nouvelles lignes qui correspondent aux filtres."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Renommer une colonne (Priority: P1)

En tant qu'utilisateur configurant un jeu de données dans le tunnel d'ingestion, je souhaite renommer une colonne directement depuis l'aperçu tabulaire afin d'adapter le modèle de données à mes besoins métier.

**Why this priority** : Le renommage est l'action la plus courante et la plus accessible — c'est la seule action disponible directement dans l'en-tête de colonne sans passer par le menu.

**Independent Test** : Peut être testé en affichant l'aperçu d'un jeu de données, en modifiant directement le nom d'une colonne (éditable dès l'affichage), et en vérifiant que le nouveau nom est pris en compte après un debounce.

**Acceptance Scenarios** :

1. **Given** l'aperçu tabulaire est affiché avec ses colonnes, **When** l'utilisateur regarde l'en-tête d'une colonne, **Then** le nom de la colonne est directement éditable (champ de saisie visible dès l'affichage, sans nécessiter de clic préalable).
2. **Given** l'utilisateur est en train d'éditer le nom d'une colonne, **When** il saisit un nouveau nom et arrête de taper pendant la durée du debounce, **Then** la configuration de transformation est mise à jour et un nouvel aperçu est demandé au backend.
3. **Given** une colonne a été renommée, **When** l'utilisateur consulte le bouton ou le menu des actions de cette colonne, **Then** aucun indicateur visuel particulier ne signale le renommage.
4. **Given** une colonne a été renommée, **When** l'utilisateur souhaite revenir au nom original, **Then** il n'existe pas de mécanisme d'annulation ; l'utilisateur doit ressaisir manuellement le nom d'origine.

---

### User Story 2 - Retirer et restaurer une colonne (Priority: P1)

En tant qu'utilisateur, je souhaite pouvoir retirer une colonne de mon jeu de données afin d'exclure les données non pertinentes, tout en conservant la possibilité de la restaurer si je change d'avis.

**Why this priority** : Le retrait de colonnes est essentiel pour nettoyer le modèle de données. La restauration d'une colonne qui a été retirée permet à l'utilisateur de corriger son action.

**Independent Test** : Peut être testé en retirant une colonne via le menu, en vérifiant son état grisé et l'icône de restauration, puis en restaurant la colonne et en vérifiant le retour à l'état normal.

**Acceptance Scenarios** :

1. **Given** l'aperçu tabulaire est affiché, **When** l'utilisateur ouvre le menu des actions d'une colonne et choisit « retirer », **Then** la colonne reste visible mais apparaît grisée.
2. **Given** une colonne est retirée (grisée), **When** l'utilisateur essaie d'ouvrir le menu des actions, **Then** le bouton du menu affiche une icône de restauration au lieu du menu standard des actions.
3. **Given** une colonne est retirée, **When** l'utilisateur tente de renommer la colonne directement dans l'en-tête, **Then** l'édition en ligne n'est pas possible (le nom n'est pas éditable).
4. **Given** une colonne est retirée, **When** l'utilisateur clique sur l'icône de restauration, **Then** la colonne redevient active et le menu des actions standard est de nouveau disponible.
5. **Given** l'utilisateur retire une colonne, **When** la configuration est envoyée au backend, **Then** un nouvel aperçu est demandé et la colonne retirée est indiquée comme telle dans le modèle de données transformé.

---

### User Story 3 - Changer le type d'une colonne (Priority: P2)

En tant qu'utilisateur, je souhaite changer le type de données d'une colonne afin de m'assurer que les données sont correctement typées pour leur exploitation ultérieure.

**Why this priority** : Le changement de type est important pour la qualité des données mais intervient après les opérations structurelles (retrait/renommage).

**Independent Test** : Peut être testé en ouvrant le menu des actions d'une colonne, en sélectionnant « changer le type », en choisissant un type dans la liste, et en vérifiant que l'aperçu est rafraîchi avec la configuration mise à jour.

**Acceptance Scenarios** :

1. **Given** l'utilisateur ouvre le menu des actions d'une colonne, **When** il sélectionne « changer le type », **Then** une liste des types prédéfinis apparaît : booléen, numérique, texte, date.
2. **Given** la liste des types est affichée, **When** l'utilisateur sélectionne un type, **Then** la configuration de transformation est immédiatement mise à jour et un nouvel aperçu est demandé au backend.
3. **Given** un type a été changé sur une colonne, **When** l'utilisateur consulte le bouton du menu des actions de cette colonne, **Then** un indicateur visuel signale qu'une action est configurée.
4. **Given** un type a été changé sur une colonne, **When** l'utilisateur ouvre le menu et regarde la ligne « changer le type », **Then** un indicateur visuel est visible sur cette ligne.

---

### User Story 4 - Filtrer une colonne (Priority: P2)

En tant qu'utilisateur, je souhaite filtrer les données d'une colonne afin de ne voir dans l'aperçu que les lignes correspondant à mes critères et de configurer la transformation en conséquence.

**Why this priority** : Le filtrage permet d'affiner la sélection des données à ingérer, ce qui est un cas d'usage clé pour la qualité des données. Il est toutefois secondaire par rapport aux opérations structurelles.

**Independent Test** : Peut être testé en appliquant un filtre sur une colonne via le menu, en le validant explicitement, en vérifiant que l'aperçu ne montre que les lignes correspondantes, puis en saisissant un nouveau filtre qui remplace le précédent, et enfin en supprimant le filtre pour vérifier le retour à l'état initial.

**Acceptance Scenarios** :

1. **Given** l'utilisateur ouvre le menu des actions d'une colonne, **When** il sélectionne « filtrer », **Then** une interface de saisie de filtre apparaît avec trois opérateurs au choix : « exactement », « contient », « commence par ».
2. **Given** l'utilisateur a choisi un opérateur et saisi une valeur de filtre, **When** il clique sur le bouton de validation du filtre, **Then** la configuration de transformation est mise à jour et un nouvel aperçu est demandé au backend avec les lignes filtrées.
3. **Given** un filtre a été validé sur une colonne, **When** l'utilisateur consulte ce filtre, **Then** le filtre n'est plus éditable.
4. **Given** un filtre validé est actif sur une colonne, **When** l'utilisateur clique sur le bouton de suppression du filtre, **Then** le filtre est supprimé, la configuration de transformation est mise à jour et un nouvel aperçu est demandé au backend.
5. **Given** une colonne a déjà un filtre actif, **When** l'utilisateur saisit un nouveau filtre et le valide, **Then** le nouveau filtre remplace l'ancien (un seul filtre par colonne à la fois).
6. **Given** des filtres sont actifs sur deux colonnes différentes, **When** l'aperçu est recalculé, **Then** les filtres se cumulent (seules les lignes satisfaisant tous les filtres actifs sont affichées).
7. **Given** un filtre est actif sur une colonne, **When** l'utilisateur consulte le bouton du menu des actions de cette colonne, **Then** un indicateur visuel signale qu'une action est configurée.

---

### User Story 5 - Accéder au menu des actions d'une colonne (Priority: P1)

En tant qu'utilisateur, je souhaite accéder rapidement aux actions disponibles sur une colonne via un bouton dans l'en-tête afin d'agir sur le modèle de données de manière fluide.

**Why this priority** : Le menu des actions est le point d'entrée unique pour toutes les transformations (sauf le renommage en ligne). Sans lui, les autres fonctionnalités ne sont pas accessibles.

**Independent Test** : Peut être testé en cliquant sur le bouton d'actions dans l'en-tête d'une colonne et en vérifiant que la liste des actions s'affiche correctement.

**Acceptance Scenarios** :

1. **Given** l'aperçu tabulaire est affiché, **When** l'utilisateur clique sur le bouton d'actions dans l'en-tête d'une colonne, **Then** une liste déroulante des actions disponibles apparaît : retirer, changer le type, filtrer.
2. **Given** aucune action n'est configurée sur une colonne, **When** l'utilisateur consulte le bouton du menu des actions, **Then** aucun indicateur visuel n'est présent sur le bouton.
3. **Given** une ou plusieurs actions sont configurées sur une colonne, **When** l'utilisateur consulte le bouton du menu des actions, **Then** un indicateur visuel est visible sur le bouton.
4. **Given** une action est configurée sur une colonne, **When** l'utilisateur ouvre le menu des actions, **Then** la ligne correspondant à l'action configurée porte un indicateur visuel distinctif.

---

### User Story 6 - Cohérence de la transformation entre aperçu, ingestion et publication (Priority: P1)

En tant qu'utilisateur, je souhaite que la transformation configurée dans l'aperçu soit exactement celle appliquée lors de l'ingestion des données dans la table finale, afin que les données publiées par GeoServer reflètent fidèlement ma configuration.

**Why this priority** : Sans cette garantie de cohérence, l'aperçu perd sa raison d'être — l'utilisateur doit pouvoir se fier à ce qu'il voit pour anticiper le résultat final.

**Independent Test** : Peut être testé en configurant des transformations (renommage, changement de type, filtre, retrait) dans l'aperçu, en validant l'étape de transformation dans le tunnel d'ingestion, puis en consultant la couche publiée dans GeoServer pour vérifier que toutes les transformations sont bien appliquées.

**Acceptance Scenarios** :

1. **Given** l'utilisateur a configuré des transformations sur les colonnes dans l'aperçu, **When** il valide l'étape de transformation dans le tunnel d'ingestion, **Then** les données ingérées dans la table finale respectent exactement la configuration de transformation (renommages, changements de type, filtres, retraits).
2. **Given** les données ont été ingérées avec la transformation configurée, **When** l'utilisateur consulte la couche correspondante dans GeoServer, **Then** les colonnes renommées portent leur nouveau nom.
3. **Given** les données ont été ingérées avec la transformation configurée, **When** l'utilisateur consulte la couche dans GeoServer, **Then** les colonnes dont le type a été changé présentent le type configuré.
4. **Given** les données ont été ingérées avec la transformation configurée, **When** l'utilisateur consulte la couche dans GeoServer, **Then** seules les lignes correspondant aux filtres actifs sont présentes.
5. **Given** les données ont été ingérées avec la transformation configurée, **When** l'utilisateur consulte la couche dans GeoServer, **Then** les colonnes retirées ne sont pas présentes.

---

### Edge Cases

- Que se passe-t-il si l'utilisateur renomme une colonne avec un nom vide ? Le système doit empêcher la validation d'un nom vide et conserver le nom précédent.
- Que se passe-t-il si l'utilisateur renomme une colonne avec un nom déjà utilisé par une autre colonne ? Le système doit signaler un conflit de noms et empêcher la validation du doublon.
- Que se passe-t-il si l'utilisateur retire toutes les colonnes ? Le système doit permettre cette action mais signaler que le jeu de données transformé sera vide.
- Que se passe-t-il si la réponse du backend dépasse la durée du timeout ? Le système revient à l'état précédant la requête ayant échoué, et une erreur est signalée (l'affichage de l'erreur ne fait pas partie de ces spécifications).
- Que se passe-t-il si l'utilisateur modifie rapidement plusieurs colonnes en succession ? Les requêtes doivent être correctement séquencées ou annulées (seule la dernière configuration compte).
- Que se passe-t-il si la valeur du filtre ne correspond à aucune ligne ? L'aperçu doit afficher un état vide avec un message indiquant qu'aucune ligne ne correspond aux critères.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système DOIT afficher un bouton d'actions dans l'en-tête de chaque colonne de l'aperçu tabulaire.
- **FR-002** : Le système DOIT afficher une liste d'actions (retirer, changer le type, filtrer) lorsque l'utilisateur clique sur le bouton d'actions d'une colonne active.
- **FR-003** : Le système DOIT afficher le nom de chaque colonne dans un champ éditable dès l'affichage de l'aperçu, permettant le renommage en ligne sans interaction préalable.
- **FR-003a** : Le système NE DOIT PAS afficher d'indicateur visuel lorsqu'une colonne a été renommée.
- **FR-003b** : Le système NE DOIT PAS proposer de mécanisme d'annulation du renommage.
- **FR-004** : Le système DOIT empêcher la validation d'un nom de colonne vide ou en doublon avec une autre colonne.
- **FR-005** : Le système DOIT griser une colonne retirée tout en la gardant visible dans l'aperçu.
- **FR-006** : Le système DOIT désactiver toutes les actions (y compris le renommage en ligne) sur une colonne retirée.
- **FR-007** : Le système DOIT remplacer le bouton du menu des actions par une icône de restauration lorsqu'une colonne est retirée.
- **FR-008** : Le système DOIT restaurer une colonne retirée à son état actif lorsque l'utilisateur clique sur l'icône de restauration.
- **FR-009** : Le système DOIT proposer exactement quatre types prédéfinis lors du changement de type : booléen, numérique, texte, date.
- **FR-010** : Le système DOIT proposer exactement trois opérateurs de filtre : « exactement », « contient », « commence par ».
- **FR-011** : Le système DOIT appliquer un seul filtre par colonne à la fois — la saisie d'un nouveau filtre sur une colonne déjà filtrée remplace le filtre précédent.
- **FR-011a** : Le système DOIT exiger une validation explicite du filtre par l'utilisateur (clic sur un bouton) avant de l'appliquer.
- **FR-011b** : Le système NE DOIT PAS permettre l'édition d'un filtre une fois validé ; l'utilisateur peut le supprimer ou en saisir un nouveau qui le remplace.
- **FR-011c** : Le système DOIT proposer un bouton de suppression pour chaque filtre validé.
- **FR-012** : Le système DOIT cumuler les filtres actifs sur différentes colonnes (intersection logique).
- **FR-013** : Le système DOIT afficher un indicateur visuel sur le bouton du menu des actions lorsqu'au moins une action (retrait, changement de type ou filtre — hors renommage) est configurée sur la colonne.
- **FR-014** : Le système DOIT afficher un indicateur visuel sur chaque ligne d'action configurée (retrait, changement de type ou filtre — hors renommage) dans le menu déroulant.
- **FR-015** : Le système DOIT appliquer la configuration de transformation immédiatement à chaque modification de l'utilisateur.
- **FR-016** : Le système DOIT appliquer un debounce sur les saisies texte de renommage avant d'envoyer la configuration au backend.
- **FR-017** : Le système DOIT demander un nouvel aperçu au backend à chaque mise à jour de la configuration de transformation, reflétant les lignes correspondant aux filtres actifs.
- **FR-017a** : L'aperçu DOIT toujours afficher au plus les 10 premières lignes de la donnée, après application des filtres.
- **FR-018** : Le système NE DOIT PAS afficher d'indicateur d'attente lors de la requête au backend.
- **FR-019** : Le système DOIT revenir à l'état précédant la requête si la réponse du backend dépasse la durée du timeout. L'affichage de l'erreur ne fait pas partie de ces spécifications.
- **FR-020** : Le système DOIT afficher un état vide explicite si les filtres actifs ne correspondent à aucune ligne.
- **FR-021** : La transformation appliquée pour générer l'aperçu DOIT être exactement la même que celle appliquée lors de l'ingestion de la donnée dans la table finale.
- **FR-022** : Lorsque l'utilisateur valide l'étape de transformation dans le tunnel d'ingestion, les données publiées par GeoServer DOIVENT respecter la transformation configurée (renommages, changements de type, filtres, retraits de colonnes).

### Key Entities

- **Colonne** : Représente une colonne du jeu de données dans l'aperçu. Attributs clés : nom (original et renommé), type de données (original et modifié), état (active ou retirée), filtre actif (opérateur + valeur).
- **Configuration de transformation** : Ensemble des actions configurées par l'utilisateur sur les colonnes (renommages, retraits, changements de type, filtres). Appliquée de manière identique pour générer l'aperçu et lors de l'ingestion dans la table finale.
- **Filtre de colonne** : Critère de filtrage appliqué à une colonne, composé d'un opérateur (exactement, contient, commence par) et d'une valeur textuelle.
- **Aperçu tabulaire** : Visualisation sous forme de tableau des 10 premières lignes (au plus) du jeu de données après application des filtres, mise à jour dynamiquement en fonction de la configuration de transformation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : L'utilisateur peut renommer, retirer, restaurer et changer le type d'une colonne en moins de 3 interactions (clics/saisies) par action. L'ajout d'un filtre, opération plus complexe (choix d'opérateur, saisie de valeur, validation), peut nécessiter davantage d'interactions.
- **SC-002** : Après une modification, l'aperçu actualisé est affiché en moins de 3 secondes (hors temps de traitement des données volumineuses).
- **SC-003** : 100 % des actions configurées (hors renommage) sur les colonnes sont reflétées par un indicateur visuel, tant sur le bouton du menu que sur la ligne d'action correspondante.
- **SC-004** : L'utilisateur peut configurer les transformations sur toutes les colonnes d'un jeu de données sans perte de données ni incohérence d'état.
- **SC-005** : Le cumul des filtres sur différentes colonnes produit un résultat cohérent (intersection logique) vérifié visuellement par l'utilisateur dans l'aperçu.
- **SC-006** : 95 % des utilisateurs parviennent à configurer une transformation complète (renommage + filtre + changement de type) lors de leur première utilisation, sans aide extérieure.
- **SC-007** : Après validation de l'étape de transformation et ingestion, 100 % des transformations configurées (renommage, changement de type, filtre, retrait) sont fidèlement reflétées dans la couche publiée par GeoServer.

## Assumptions

- L'aperçu tabulaire existe déjà dans le tunnel d'ingestion et affiche les données du jeu de données.
- Le backend ne dispose pas encore d'un mécanisme pour recevoir une configuration de transformation et renvoyer un aperçu filtré ; ce mécanisme devra être implémenté dans le cadre de cette fonctionnalité.
- Le backend est capable de régénérer rapidement un nouvel aperçu avec les transformations mises à jour, sans nécessiter d'indicateur d'attente côté interface.
- Le debounce sur les saisies texte utilise un délai raisonnable (par exemple 300-500 ms), le délai exact étant un détail d'implémentation.
- Le jeu de données comporte un nombre raisonnable de colonnes affichables dans une vue tabulaire (pas de scroll horizontal infini).
- Les types prédéfinis (booléen, numérique, texte, date) couvrent les besoins métier actuels et ne nécessitent pas de types personnalisés dans cette itération.
- Les opérateurs de filtre (exactement, contient, commence par) opèrent sur la représentation textuelle des valeurs de la colonne.
