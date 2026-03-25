## Context

GeoNetwork metadata records store citation dates including creation, publication, and revision. In the current implementation:

- **Initial ingestion** generates metadata via XSLT transformation of an ISO 19115-3 template. The `mdb:dateInfo[revision]` field remains at the template default (`1970-01-01`) because the XSLT 2.0 `format-dateTime()` calls are commented out (lxml supports XSLT 1.0 only) and no `revisionDate` property is passed from Python. The citation dates (`cit:date[1]` = creation, `cit:date[2]` = publication) are populated but no citation revision date exists.
- **Recurrence** (scheduled re-ingestion) calls `dag_success_callback` which updates `last_retrieval_timestamp` but never touches the GeoNetwork record.
- **Reconfiguration** (re-processing through the tunnel with an existing metadata record) skips metadata creation entirely (`if integrity_link.metadata_id is None:` guard).
- There is no `update_revision_date()` or record-patching method in `MetadataService`.

The ticket (GSMEL-979) requires that both ISO 19115-3 and ISO 19139 schemas are supported when updating revision dates.

## Goals / Non-Goals

**Goals:**
- Set revision date correctly on initial metadata generation (same as creation date)
- Update the revision date in the GeoNetwork record after each successful recurrence run
- Update the revision date after a successful reconfiguration
- Support both ISO 19115-3 and ISO 19139 metadata schemas when patching revision dates
- Add a citation-level revision date (`cit:date` with `codeListValue="revision"`) in addition to the metadata-level `mdb:dateInfo[revision]`

**Non-Goals:**
- Frontend changes (no UI for revision dates)
- Modifying the recurrence DAG logic itself (only the backend callback changes)
- Supporting schemas other than ISO 19115-3 and ISO 19139
- Changing when or how creation/publication dates are set beyond fixing the initial `1970-01-01` default

## Decisions

### D1: Patch-in-place via GeoNetwork API (fetch → modify → re-upload)

Fetch the existing XML record from GeoNetwork, parse it, locate or insert the revision date element, then re-upload with `uuidprocessing="OVERWRITE"`.

**Why**: The existing `publish_metadata()` already uses `OVERWRITE` mode. Fetching the current record ensures we preserve any manual edits made in GeoNetwork. A full re-generation from template would overwrite external changes.

**Alternative considered**: Re-generate metadata from template with updated properties. Rejected because it would overwrite any manual metadata edits made directly in GeoNetwork.

### D2: Dual schema detection via root namespace

Detect the schema by checking the root element's namespace:
- `http://standards.iso.org/iso/19115/-3/mdb/2.0` → ISO 19115-3
- `http://www.isotc211.org/2005/gmd` → ISO 19139

Each schema has different XPaths for the revision date. The method will branch based on the detected schema.

**Why**: This is the standard approach for ISO metadata and matches the pattern suggested in the JIRA ticket.

### D3: New `MetadataService.update_revision_date()` method

Add a single method `update_revision_date(metadata_uuid: str, revision_date: datetime)` to `MetadataService` that:
1. Fetches the XML from GeoNetwork via `gn_api`
2. Detects the schema (19115-3 vs 19139)
3. Finds the existing revision date element, or creates one if absent
4. Sets the date value to the provided timestamp
5. Re-uploads the modified XML

**Why**: Follows the existing service layer pattern. Keeps the XML manipulation in `MetadataService` where all metadata operations live.

### D4: Fix initial generation — add `revisionDate` property and XSLT template

In `generate_metadata()`, add a `revisionDate` property (set to `creationDate`) and add XSLT 1.0 templates to populate:
- `mdb:dateInfo[2]` (metadata-level revision) from `$props//revisionDate`
- A new third `cit:date` element with `codeListValue="revision"` in the citation

**Why**: Fixes the `1970-01-01` default. Uses the same XSLT 1.0 approach as the existing creation/publication date templates (no XSLT 2.0 functions needed — the date string is pre-formatted in Python).

### D5: Call update in `dag_success_callback` (recurrence + reconfiguration)

Both recurrence and reconfiguration end at `dag_success_callback`. Add one call at the end of the callback:

```python
if integrity_link.metadata_id is not None:
    metadata_service.update_revision_date(
        str(integrity_link.id), datetime.now(timezone.utc)
    )
```

**Why**: `dag_success_callback` is the single convergence point for both flows. No DAG code changes needed. The `MetadataService` instantiation will be added to the callback (currently only used in `process_staging_data`).

**Alternative considered**: Separate calls in recurrence path vs reconfiguration path. Rejected because both converge at `dag_success_callback` already.

### D6: Soft failure for revision date update

If `update_revision_date()` fails, log a warning but do not fail the callback. The data ingestion is the primary operation; metadata date update is secondary.

**Why**: Consistent with how ownership assignment already handles failures (`logger.warning` + continue).

## Risks / Trade-offs

- **[GeoNetwork API availability]** → If GeoNetwork is temporarily unavailable during callback, the revision date won't be updated. Mitigation: log a warning. The date will be corrected on the next recurrence run.
- **[Concurrent edits]** → If someone edits the record in GeoNetwork while we fetch-modify-upload, their changes could be lost. Mitigation: the time window is very small (fetch-modify-upload in same call). Acceptable risk for this use case.
- **[ISO 19139 records]** → We only generate 19115-3 templates, but existing records may be in 19139 format. The update method must handle both, but we won't have 19139 records to test internally. Mitigation: the namespace detection + XPath approach is well-documented in ISO standards.
