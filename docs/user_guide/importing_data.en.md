# Importing a dataset

Importing a dataset is done in two stages, both tracked on the same record (an *IntegrityLink*, one per dataset):
**staging** the raw data, then **processing** it into its published form.

## 1. Choose a source

The import wizard supports the following source types:

| Source     | Description                                                             |
|------------|--------------------------------------------------------------------------|
| **File**   | CSV, GeoPackage, GeoJSON, zipped Shapefile, Parquet or GeoParquet upload |
| **URL**    | Same file formats, fetched from a remote HTTP(S) URL                     |
| **FTP**    | Same file formats, fetched from an FTP server                            |
| **Database** | A table or query read from one of the configured source databases      |
| **API**    | An OGC service: WFS or OGC API Features                                  |

Once submitted, Datafeeder ingests the raw source into a **staging table** in PostgreSQL, with no transformation
applied yet. This step lets you inspect the actual columns, geometry and data types before deciding how to publish
them.

!!! note "Re-staging"

    If the staging step needs to be redone (wrong file, source moved, credentials changed), you don't need to start
    over: editing the source configuration on an existing dataset re-triggers staging without losing the rest of the
    configuration.

## 2. Configure the transformation

Once staged, you configure how the data should be transformed into its final, published form:

- **Column mapping**: rename, drop or retype columns
- **Projection**: reproject the geometry to a target CRS (the available projections are configured platform-wide)
- **Filters**: restrict the rows carried over to the final table

## 3. Publish

Submitting the transformation writes the final table, then:

- creates the GeoNetwork metadata record for the dataset
- publishes the corresponding layer on GeoServer

If anything fails at this stage, the partial final table is dropped so the dataset never ends up in a half-published
state.

## Recurring imports

A dataset can be configured to automatically re-fetch from its original source and re-run the transformation on a
schedule (every minute, hour, day, week, month or year). This is useful for sources that change over time, such as
an OGC service or a periodically updated file at a fixed URL. See [Managing datasets](managing_datasets.md) for how
to configure and monitor a recurring import.

## Empty datasets

It is also possible to create a dataset with no source at all (**empty dataset**): Datafeeder creates the
`IntegrityLink` record and a skeleton GeoNetwork metadata record immediately, with no data pipeline involved. This is
useful to reserve a metadata record ahead of publishing data manually, or for datasets that live entirely on
GeoServer already.
