## 1. Fix initial metadata generation

- [x] 1.1 Remove the `mdb:dateInfo` element with `codeListValue="revision"` from `docker/datadir/datafeeder-python/metadata_template-19115-3.xml`
- [x] 1.2 Add XSLT 1.0 template in `docker/datadir/datafeeder-python/metadata_transform-19115-3.xsl` to populate `mdb:dateInfo[1]` (creation) from `$props//creationDate`

## 2. Implement `update_revision_date()` method

- [x] 2.1 Add namespace maps for ISO 19115-3 and ISO 19139 as class constants in `MetadataService` (`apps/backend/src/services/metadata_service.py`)
- [x] 2.2 Implement `_detect_schema(root)` private method that returns the schema type based on root element namespace
- [x] 2.3 Implement `_update_revision_date_19115_3(root, date)` that locates or inserts the data revision date in `mri:citation/cit:CI_Citation/cit:date`: detect existing `gco:DateTime` or `gco:Date` and replace with `gco:DateTime`; insert `gco:DateTime` when absent (`mdb:dateInfo` must not be modified)
- [x] 2.4 Implement `_update_revision_date_19139(root, date)` that locates or inserts the data revision date in `gmd:identificationInfo/.../gmd:CI_Citation/gmd:date`: detect existing `gco:DateTime` or `gco:Date` and replace with `gco:DateTime`; insert `gco:DateTime` when absent
- [x] 2.5 Implement `update_revision_date(metadata_uuid, revision_date)` public method that fetches XML from GeoNetwork, detects schema, calls the appropriate updater, and saves via GeoNetwork save endpoint (PUT `/records/{uuid}`, not re-publish)

## 3. Integrate into ingestion callbacks

- [x] 3.1 In `dag_success_callback` (`apps/backend/src/api/routes/ingestion/process.py`), instantiate `MetadataService` and call `update_revision_date()` when `integrity_link.metadata_id is not None`, with soft failure (log warning on error)

## 4. Testing

- [x] 4.1 [P] Unit tests for `_detect_schema()` with ISO 19115-3, ISO 19139, and unsupported root elements
- [x] 4.2 [P] Unit tests for `_update_revision_date_19115_3()` — insert when absent (→ `gco:DateTime`), replace existing `gco:DateTime`, replace existing `gco:Date` (→ `gco:DateTime`)
- [x] 4.3 [P] Unit tests for `_update_revision_date_19139()` — insert when absent (→ `gco:DateTime`), replace existing `gco:DateTime`, replace existing `gco:Date` (→ `gco:DateTime`)
- [x] 4.4 Unit test for `update_revision_date()` — mock GeoNetwork fetch/save, verify end-to-end flow
- [x] 4.5 Unit test for `generate_metadata()` — verify creation date is set correctly (not `1970-01-01`) and no revision date is present
- [x] 4.6 Run `make fix-all-python` to ensure linting/formatting compliance
