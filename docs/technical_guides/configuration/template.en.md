# Guide de Conception des Templates XML de Métadonnées (ISO 19115-3)

Ce guide est destiné aux rédacteurs et gestionnaires de données non techniciens. Il définit les règles de structure que doivent respecter vos templates XML pour que le système puisse automatiquement y injecter les informations métier lors des transformations.

Ce guide n'est valide que pour le XSL livré par défaut avec le Datafeeder. En cas de surcharge du XSL au déploiement, les règles de structure devront être adaptées.

---

## 💡 Principe Général

Le moteur de traitement utilise vos templates XML comme **gabarits de départ**.
Lors de la génération finale :
- La plupart de vos éléments et attributs de structure sont conservés à l'identique.
- Certaines balises cibles spécifiques sont repérées et **leurs valeurs sont automatiquement remplacées ou enrichies** par le système.

---

## 📐 Règles de Structure & Balises Requises

Pour que les données métier s'injectent correctement, votre template doit impérativement respecter les emplacements et l'ordre des éléments décrits ci-dessous.

### 1. Identifiant & Titrage
* **Identifiant du fichier** : Doit contenir une balise `<gco:CharacterString>` sous `mdb:metadataIdentifier/mcc:MD_Identifier/mcc:code/`.
* **Titre du jeu de données** : Doit être placé dans `gco:CharacterString` sous `mri:citation/cit:CI_Citation/cit:title/`.
* **Résumé / Description** : Doit être placé dans `gco:CharacterString` sous `mri:abstract/`.

### 2. Dates de la Fiche
Dans le bloc `cit:CI_Citation`, **l'ordre des dates est primordial** :
* **1<sup>ère</sup> date (`cit:date[1]`)** : Réservée pour la **date de création** du jeu de données.
* **2<sup>ème</sup> date (`cit:date[2]`)** : Réservée pour la **date de publication** de la métadonnée.
* **Date d'horodatage globale** : Déclarée séparément sous `mdb:dateInfo/cit:CI_Date/cit:date/gco:DateTime`.

### 3. Contacts & Organismes Responsables
* **Responsable des données** : Le système ajoutera le contact officiel **juste après le dernier bloc `<mri:pointOfContact>`** existant dans votre template.
* **Responsable de la fiche de métadonnées** : Le système l'ajoutera **juste après le dernier bloc `<mdb:contact>`**.
> ⚠️ **Important** : Laissez au moins un bloc conteneur vide ou d'exemple dans votre template pour marquer l'emplacement où le système doit rattacher ces contacts.

### 4. Couverture Géographique & Résolution
* **Boîte englobante (Emprise)** : Inclure le nœud `<gex:EX_GeographicBoundingBox>` sous `mri:extent/gex:EX_Extent/gex:geographicElement/`. Les 4 coordonnées (*West, East, South, North*) seront injectées automatiquement.
* **Résolution / Échelle** : La valeur numérique du dénominateur d'échelle sera insérée sous `mri:spatialResolution/.../mri:denominator/gco:Integer`.
* **Système de coordonnées** : Le code du système (ex: EPSG) sera placé sous `mdb:referenceSystemInfo/.../mcc:code/gco:CharacterString`.

### 5. Liens & Téléchargements
* **Ressources en ligne** : Les liens de téléchargement et accès aux services web seront automatiquement générés et insérés sous l'élément `mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions`.

---

## 📄 Exemple Complet de Template XML (Modèle de départ)

Voici un exemple minimal et valide de template XML que vous pouvez copier/coller comme base de travail :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
                 xmlns:mcc="http://standards.iso.org/iso/19115/-3/mcc/1.0"
                 xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:gex="http://standards.iso.org/iso/19115/-3/gex/1.0"
                 xmlns:mrs="http://standards.iso.org/iso/19115/-3/mrs/1.0"
                 xmlns:lan="http://standards.iso.org/iso/19115/-3/lan/1.0"
                 xmlns:mrd="http://standards.iso.org/iso/19115/-3/mrd/1.0"
                 xmlns:mrl="http://standards.iso.org/iso/19115/-3/mrl/2.0">

  <!-- 1. Identifiant de la fiche -->
  <mdb:metadataIdentifier>
    <mcc:MD_Identifier>
      <mcc:code>
        <gco:CharacterString>ID_TEMPORAIRE</gco:CharacterString>
      </mcc:code>
    </mcc:MD_Identifier>
  </mdb:metadataIdentifier>

  <!-- 2. Encodage des caractères -->
  <mdb:defaultLocale>
    <lan:PT_Locale>
      <lan:characterEncoding>
        <lan:MD_CharacterSetCode codeListValue="utf8"/>
      </lan:characterEncoding>
    </lan:PT_Locale>
  </mdb:defaultLocale>

  <!-- 3. Contact de la métadonnée (Emplacement d'insertion) -->
  <mdb:contact>
    <!-- Le contact officiel de la fiche sera ajouté automatiquement à la suite -->
  </mdb:contact>

  <!-- 4. Date de mise à jour de la fiche -->
  <mdb:dateInfo>
    <cit:CI_Date>
      <cit:date>
        <gco:DateTime>2026-01-01T00:00:00</gco:DateTime>
      </cit:date>
    </cit:CI_Date>
  </mdb:dateInfo>

  <!-- 5. Informations sur la donnée -->
  <mdb:identificationInfo>
    <mri:MD_DataIdentification>

      <!-- Citation : Titre et Dates -->
      <mri:citation>
        <cit:CI_Citation>
          <cit:title>
            <gco:CharacterString>Titre temporaire du jeu de données</gco:CharacterString>
          </cit:title>

          <!-- Date 1 : Création de la donnée -->
          <cit:date>
            <cit:CI_Date>
              <cit:date>
                <gco:Date>2026-01-01</gco:Date>
              </cit:date>
            </cit:CI_Date>
          </cit:date>

          <!-- Date 2 : Publication de la métadonnée -->
          <cit:date>
            <cit:CI_Date>
              <cit:date>
                <gco:Date>2026-01-01</gco:Date>
              </cit:date>
            </cit:CI_Date>
          </cit:date>
        </cit:CI_Citation>
      </mri:citation>

      <!-- Résumé -->
      <mri:abstract>
        <gco:CharacterString>Résumé / description de la donnée à modifier...</gco:CharacterString>
      </mri:abstract>

      <!-- Représentation spatiale (Ex: Vectoriel, Raster) -->
      <mri:spatialRepresentationType>
        <mcc:MD_SpatialRepresentationTypeCode codeListValue="vector"/>
      </mri:spatialRepresentationType>

      <!-- Échelle / Résolution -->
      <mri:spatialResolution>
        <mri:MD_Resolution>
          <mri:equivalentScale>
            <mri:MD_RepresentativeFraction>
              <mri:denominator>
                <gco:Integer>25000</gco:Integer>
              </mri:denominator>
            </mri:MD_RepresentativeFraction>
          </mri:equivalentScale>
        </mri:MD_Resolution>
      </mri:spatialResolution>

      <!-- Point de contact du jeu de données (Emplacement d'insertion) -->
      <mri:pointOfContact>
        <!-- Le contact du jeu de données sera inséré automatiquement à la suite -->
      </mri:pointOfContact>

      <!-- Emprise géographique -->
      <mri:extent>
        <gex:EX_Extent>
          <gex:geographicElement>
            <gex:EX_GeographicBoundingBox/>
          </gex:geographicElement>
        </gex:EX_Extent>
      </mri:extent>

    </mri:MD_DataIdentification>
  </mdb:identificationInfo>

  <!-- 6. Système de référence spatiale -->
  <mdb:referenceSystemInfo>
    <mrs:MD_ReferenceSystem>
      <mrs:referenceSystemIdentifier>
        <mcc:MD_Identifier>
          <mcc:code>
            <gco:CharacterString>EPSG:2154</gco:CharacterString>
          </mcc:code>
        </mcc:MD_Identifier>
      </mrs:referenceSystemIdentifier>
    </mrs:MD_ReferenceSystem>
  </mdb:referenceSystemInfo>

  <!-- 7. Historique / Généalogie -->
  <mdb:resourceLineage>
    <mrl:LI_Lineage>
      <mrl:statement>
        <gco:CharacterString>Origine et historique de la donnée...</gco:CharacterString>
      </mrl:statement>
    </mrl:LI_Lineage>
  </mdb:resourceLineage>

  <!-- 8. Distribution et liens en ligne -->
  <mdb:distributionInfo>
    <mrd:MD_Distribution>
      <mrd:transferOptions/>
    </mrd:MD_Distribution>
  </mdb:distributionInfo>

</mdb:MD_Metadata>
```
