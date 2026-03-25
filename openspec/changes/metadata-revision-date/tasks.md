## 1. Fix initial metadata generation

- [ ] 1.1 Add `revisionDate` property in `MetadataService.generate_metadata()` (`apps/backend/src/services/metadata_service.py`) — set to same value as `creationDate`
- [ ] 1.2 Add XSLT 1.0 templates in `docker/datadir/datafeeder-python/metadata_transform-19115-3.xsl` to populate `mdb:dateInfo[2]` (revision) from `$props//revisionDate`
- [ ] 1.3 Add a third `cit:date` element with `codeListValue="revision"` in `docker/datadir/datafeeder-python/metadata_template-19115-3.xml` and matching XSLT template to populate it from `$props//revisionDate`

## 2. Implement `update_revision_date()` method

- [ ] 2.1 Add namespace maps for ISO 19115-3 and ISO 19139 as class constants in `MetadataService` (`apps/backend/src/services/metadata_service.py`)
- [ ] 2.2 Implement `_detect_schema(root)` private method that returns the schema type based on root element namespace
- [ ] 2.3 Implement `_update_revision_date_19115_3(root, date)` that locates or inserts the revision date in `mdb:dateInfo` and `mri:citation/cit:CI_Citation/cit:date`
- [ ] 2.4 Implement `_update_revision_date_19139(root, date)` that locates or inserts the revision date in `gmd:identificationInfo/.../gmd:CI_Citation/gmd:date`
- [ ] 2.5 Implement `update_revision_date(metadata_uuid, revision_date)` public method that fetches XML from GeoNetwork, detects schema, calls the appropriate updater, and re-uploads

## 3. Integrate into ingestion callbacks

- [ ] 3.1 In `dag_success_callback` (`apps/backend/src/api/routes/ingestion/process.py`), instantiate `MetadataService` and call `update_revision_date()` when `integrity_link.metadata_id is not None`, with soft failure (log warning on error)

## 4. Testing

- [ ] 4.1 [P] Unit tests for `_detect_schema()` with ISO 19115-3, ISO 19139, and unsupported root elements
- [ ] 4.2 [P] Unit tests for `_update_revision_date_19115_3()` — insert when absent, replace when present
- [ ] 4.3 [P] Unit tests for `_update_revision_date_19139()` — insert when absent, replace when present
- [ ] 4.4 Unit test for `update_revision_date()` — mock GeoNetwork fetch/upload, verify end-to-end flow
- [ ] 4.5 Unit test for `generate_metadata()` — verify revision date is set correctly on initial generation (not `1970-01-01`)
- [ ] 4.6 Run `make fix-all-python` to ensure linting/formatting compliance
