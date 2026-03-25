## Context

GeoNetwork metadata records store citation dates including creation, publication, and revision. In the current implementation:

- **Initial ingestion** generates metadata via XSLT transformation of an ISO 19115-3 template. The `mdb:dateInfo[creation]` field remains at the template default (`1970-01-01`) because the XSLT 2.0 `format-dateTime()` calls are commented out (lxml supports XSLT 1.0 only) and no XSLT 1.0 template populates it. The template also contains a `mdb:dateInfo[revision]` placeholder that should not be present at initial creation. The citation dates (`cit:date[1]` = creation, `cit:date[2]` = publication) are populated but the metadata-level creation date is not.
- **Recurrence** (scheduled re-ingestion) calls `dag_success_callback` which updates `last_retrieval_timestamp` but never touches the GeoNetwork record.
- **Reconfiguration** (re-processing through the tunnel with an existing metadata record) skips metadata creation entirely (`if integrity_link.metadata_id is None:` guard).
- There is no `update_revision_date()` or record-patching method in `MetadataService`.

The ticket (GSMEL-979) requires that both ISO 19115-3 and ISO 19139 schemas are supported when updating revision dates.

## Goals / Non-Goals

**Goals:**
- Fix the creation date (`mdb:dateInfo[creation]`) on initial metadata generation (instead of `1970-01-01`)
- Remove the revision date placeholder from the XML template (no revision date at initial creation)
- Update the revision date in the GeoNetwork record after each successful recurrence run
- Update the revision date after a successful reconfiguration
- Support both ISO 19115-3 and ISO 19139 metadata schemas when patching revision dates
- Use GeoNetwork save (not re-publish) when updating revision dates — save preserves the record without altering its publication status

**Non-Goals:**
- Frontend changes (no UI for revision dates)
- Modifying the recurrence DAG logic itself (only the backend callback changes)
- Supporting schemas other than ISO 19115-3 and ISO 19139
- Setting a revision date at initial creation (only on subsequent updates)

## Decisions

### D1: Patch-in-place via GeoNetwork API (fetch → modify → save)

Fetch the existing XML record from GeoNetwork, parse it, locate or insert the revision date element, then save using the GeoNetwork record save endpoint (PUT `/records/{uuid}`). This is distinct from `publish_metadata()` which uses `upload_metadata()` with `OVERWRITE` — save updates the record content without affecting its publication status.

**Why**: GeoNetwork distinguishes between "save" (update record XML) and "publish" (make record visible/public). Using save preserves the current publication state. Fetching the current record ensures we preserve any manual edits made in GeoNetwork.

**Alternative considered**: Re-upload with `upload_metadata(uuidprocessing="OVERWRITE")`. Rejected because it could alter publication status and is heavier than a simple save.

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
5. Saves the modified XML via GeoNetwork save endpoint (PUT `/records/{uuid}`, not re-publish)

**Why**: Follows the existing service layer pattern. Keeps the XML manipulation in `MetadataService` where all metadata operations live. Using save instead of re-publish avoids altering the record's publication status.

### D4: Fix initial generation — remove revision date, fix creation date

In the XML template, remove the `mdb:dateInfo` element with `codeListValue="revision"` — a revision date should not exist at initial creation (the data hasn't been revised yet). Add an XSLT 1.0 template to populate `mdb:dateInfo[1]` (creation) from `$props//creationDate`, replacing the hardcoded `1970-01-01` placeholder. The creation date is already set in Python as `integrity_link.created_at`.

**Why**: The revision date is semantically different from creation — it only makes sense after the data has been updated at least once. The creation date fix uses the same XSLT 1.0 approach as existing templates.

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
- **[Concurrent edits]** → If someone edits the record in GeoNetwork while we fetch-modify-save, their changes could be lost. Mitigation: the time window is very small (fetch-modify-save in same call). Acceptable risk for this use case.
- **[ISO 19139 records]** → We only generate 19115-3 templates, but existing records may be in 19139 format. The update method must handle both, but we won't have 19139 records to test internally. Mitigation: the namespace detection + XPath approach is well-documented in ISO standards.
