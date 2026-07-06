---
hide:
  - navigation
  - toc
---

# Datafeeder: ingesting and publishing data in geOrchestra

!!! note "Note"

    This documentation is a work in progress. It documents the Datafeeder module, in active development in 2026.

## Why ?

Publishing a dataset in a Spatial Data Infrastructure usually means juggling several tools by hand: uploading a file
or connecting to a source, staging it in a database, fixing up columns and projections, publishing a layer on
GeoServer, writing a metadata record on GeoNetwork, and eventually keeping all of that in sync when the source data
changes.

Datafeeder brings this into a single guided workflow, from source to published layer, with a dashboard to track every
dataset's state and to keep it up to date over time.

## What ?

Datafeeder is a data ingestion module for geOrchestra. It manages the full lifecycle of a dataset (geospatial or
not): upload/sourcing → staging → transformation → publication → recurring refresh.

It supports CSV, GeoPackage, GeoJSON, zipped Shapefile, Parquet and GeoParquet files, as well as OGC services
(WFS / OGC API Features), FTP and database sources.

- **[User guide](user_guide/index.md)**: how to import, transform, publish and maintain a dataset day to day.
- **[Install guide](technical_guides/index.md)**: how to deploy and configure Datafeeder on a geOrchestra platform.
- **[Contribute](technical_guides/contribute/index.md)**: how the project is built, and how to work on it.
