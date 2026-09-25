# Metadata XML Template Design Guide (ISO 19115-3)

This guide is intended for non-technical authors and data managers. It defines the structural rules that your XML templates must follow so that the system can automatically inject business information into them during XSL transformations.

This guide is only valid for the default XSL delivered with Datafeeder. If the XSL is overridden during deployment, the structural rules will need to be adapted.

---

## 💡 General Concept

The processing engine uses your XML templates as **starting blueprints**.
During final document generation:
- Most of your structural elements and attributes are preserved as-is.
- Specific target XML tags are identified, and **their values are automatically replaced or enriched** by the system.

---

## 📐 Structural Rules & Required Tags

To ensure that business data is correctly injected, your template must strictly respect the locations and order of the elements described below.

### 1. Identifier & Titles
* **File Identifier**: Must contain a `<gco:CharacterString>` tag under `mdb:metadataIdentifier/mcc:MD_Identifier/mcc:code/`.
* **Dataset Title**: Must be placed in a `gco:CharacterString` under `mri:citation/cit:CI_Citation/cit:title/`.
* **Abstract / Description**: Must be placed in a `gco:CharacterString` under `mri:abstract/`.

### 2. Record Dates
In the `cit:CI_Citation` block, **the order of the dates is critical**:
* **1<sup>st</sup> date (`cit:date[1]`)**: Reserved for the dataset **creation date**.
* **2<sup>nd</sup> date (`cit:date[2]`)**: Reserved for the metadata **publication date**.
* **Global Timestamp Date**: Declared separately under `mdb:dateInfo/cit:CI_Date/cit:date/gco:DateTime`.

### 3. Contacts & Responsible Organizations
* **Dataset Responsible Party**: The system will add the official contact **immediately after the last `<mri:pointOfContact>` block** existing in your template.
* **Metadata Record Responsible Party**: The system will add it **immediately after the last `<mdb:contact>` block**.
> ⚠️ **Important**: Keep at least one empty or sample container block in your template to mark the location where the system should append these contacts.

### 4. Geographic Extent & Resolution
* **Bounding Box (Extent)**: Include the `<gex:EX_GeographicBoundingBox>` node under `mri:extent/gex:EX_Extent/gex:geographicElement/`. The 4 coordinates (*West, East, South, North*) will be injected automatically.
* **Resolution / Scale**: The numerical value of the scale denominator will be inserted under `mri:spatialResolution/.../mri:denominator/gco:Integer`.
* **Coordinate Reference System**: The system code (e.g., EPSG) will be placed under `mdb:referenceSystemInfo/.../mcc:code/gco:CharacterString`.

### 5. Links & Downloads
* **Online Resources**: Download links and web service endpoints will be automatically generated and inserted under the `mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions` element.

---

## 📄 Complete XML Template Example (Starter Blueprint)

Here is a minimal, valid XML template example that you can copy and paste as your base working file:

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

  <!-- 1. Metadata File Identifier -->
  <mdb:metadataIdentifier>
    <mcc:MD_Identifier>
      <mcc:code>
        <gco:CharacterString>TEMPORARY_ID</gco:CharacterString>
      </mcc:code>
    </mcc:MD_Identifier>
  </mdb:metadataIdentifier>

  <!-- 2. Character Encoding -->
  <mdb:defaultLocale>
    <lan:PT_Locale>
      <lan:characterEncoding>
        <lan:MD_CharacterSetCode codeListValue="utf8"/>
      </lan:characterEncoding>
    </lan:PT_Locale>
  </mdb:defaultLocale>

  <!-- 3. Metadata Contact (Insertion Point) -->
  <mdb:contact>
    <!-- Official metadata contact will be appended automatically here -->
  </mdb:contact>

  <!-- 4. File Timestamp / Update Date -->
  <mdb:dateInfo>
    <cit:CI_Date>
      <cit:date>
        <gco:DateTime>2026-01-01T00:00:00</gco:DateTime>
      </cit:date>
    </cit:CI_Date>
  </mdb:dateInfo>

  <!-- 5. Identification Information -->
  <mdb:identificationInfo>
    <mri:MD_DataIdentification>

      <!-- Citation: Title and Dates -->
      <mri:citation>
        <cit:CI_Citation>
          <cit:title>
            <gco:CharacterString>Temporary Dataset Title</gco:CharacterString>
          </cit:title>

          <!-- Date 1: Dataset Creation Date -->
          <cit:date>
            <cit:CI_Date>
              <cit:date>
                <gco:Date>2026-01-01</gco:Date>
              </cit:date>
            </cit:CI_Date>
          </cit:date>

          <!-- Date 2: Metadata Publication Date -->
          <cit:date>
            <cit:CI_Date>
              <cit:date>
                <gco:Date>2026-01-01</gco:Date>
              </cit:date>
            </cit:CI_Date>
          </cit:date>
        </cit:CI_Citation>
      </mri:citation>

      <!-- Abstract -->
      <mri:abstract>
        <gco:CharacterString>Dataset abstract / description to be replaced...</gco:CharacterString>
      </mri:abstract>

      <!-- Spatial Representation Type (e.g., vector, grid) -->
      <mri:spatialRepresentationType>
        <mcc:MD_SpatialRepresentationTypeCode codeListValue="vector"/>
      </mri:spatialRepresentationType>

      <!-- Spatial Resolution / Scale -->
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

      <!-- Dataset Point of Contact (Insertion Point) -->
      <mri:pointOfContact>
        <!-- Dataset contact will be appended automatically here -->
      </mri:pointOfContact>

      <!-- Geographic Extent -->
      <mri:extent>
        <gex:EX_Extent>
          <gex:geographicElement>
            <gex:EX_GeographicBoundingBox/>
          </gex:geographicElement>
        </gex:EX_Extent>
      </mri:extent>

    </mri:MD_DataIdentification>
  </mdb:identificationInfo>

  <!-- 6. Coordinate Reference System -->
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

  <!-- 7. Lineage / History -->
  <mdb:resourceLineage>
    <mrl:LI_Lineage>
      <mrl:statement>
        <gco:CharacterString>Dataset background and lineage statement...</gco:CharacterString>
      </mrl:statement>
    </mrl:LI_Lineage>
  </mdb:resourceLineage>

  <!-- 8. Distribution & Online Resources -->
  <mdb:distributionInfo>
    <mrd:MD_Distribution>
      <mrd:transferOptions/>
    </mrd:MD_Distribution>
  </mdb:distributionInfo>

</mdb:MD_Metadata>
```
