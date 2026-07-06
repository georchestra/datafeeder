# Editing metadata

Every dataset with a source (as opposed to an [empty dataset](importing_data.md#empty-datasets)) gets a GeoNetwork
metadata record as soon as it is processed. The **metadata** step of the dataset editor lets you fill in and edit
that ISO 19139 record without leaving Datafeeder.

It embeds GeoNetwork's own record editor (via the `geonetwork-ui` library), so the fields and validation are the
same ones you would find in GeoNetwork directly: title, abstract, keywords, contact, spatial extent, etc.

While the processing DAG is still running, the metadata editor shows the task's live status instead (queued /
running) and unlocks once the dataset finishes processing.

A link to open the published record directly in the GeoNetwork catalogue is available once the metadata is saved.
