## Why

The revision date in GeoNetwork metadata records is never set to a meaningful value and never updated after initial ingestion. The `mdb:dateInfo[revision]` stays at the template default (`1970-01-01`), and neither recurrence nor reconfiguration flows touch the metadata record. For recurring datasets, this date is critical — it tells users when the data was last refreshed. JIRA: GSMEL-979.

## What Changes

- **Remove revision date from template**: remove the `mdb:dateInfo[revision]` placeholder from the XML template — revision dates are only set on subsequent updates, not at initial creation.
- **Fix creation date on initial ingestion**: ensure the `mdb:dateInfo[creation]` is correctly populated with the dataset creation date (instead of `1970-01-01`).
- **Update on recurrence**: after a successful recurrence DAG run, update the revision date in the GeoNetwork record to the current timestamp.
- **Update on reconfiguration**: when a dataset is reconfigured (re-ingested through the tunnel with an existing metadata record), update the revision date.
- **Support both ISO schemas**: handle revision date updates in both ISO 19115-3 (`mri:citation/cit:CI_Citation/cit:date`) and ISO 19139 (`gmd:identificationInfo/.../gmd:CI_Citation/gmd:date`) metadata records — targeting only the **data** revision date, not the metadata record date (`mdb:dateInfo` / `gmd:dateStamp`).
- **Add a `MetadataService.update_revision_date()` method**: fetch the existing XML from GeoNetwork, locate/insert/replace the revision date element, and save (without re-publishing).

## Capabilities

### New Capabilities

- `metadata-revision-date`: Add and manage revision dates in GeoNetwork metadata records — covering initial creation, recurrence updates, and reconfiguration updates, with dual ISO schema support.

### Modified Capabilities

_(none — no existing spec-level requirements change)_

## Impact

- **Backend** (`apps/backend/src/services/metadata_service.py`): new method to fetch, patch, and save metadata XML with an updated revision date (using GeoNetwork save, not re-publish).
- **Backend** (`apps/backend/src/api/routes/ingestion/process.py`): call revision date update in `dag_success_callback` and in the reconfiguration path.
- **ELT** (`apps/elt/dags/`): no direct change — recurrence DAGs already call the backend callback which will be updated.
- **Template** (`docker/datadir/datafeeder-python/metadata_template-19115-3.xml`): remove the `mdb:dateInfo[revision]` placeholder, fix `mdb:dateInfo[creation]` so XSLT populates it correctly.
- **XSLT** (`docker/datadir/datafeeder-python/metadata_transform-19115-3.xsl`): populate the creation date from properties on initial generation.
- **No frontend changes** — this is a backend-only change.
- **No breaking API changes**.
