"""Constants used across the data_manipulation library."""

DEFAULT_GEOMETRY_COLUMN = "geom"
DB_URI_PREFIX = "db://"

# OGC API - Features serves GeoJSON, which RFC 7946 pins to WGS84 lon/lat. GDAL
# does not always stamp an SRID on the loaded geometry (it ends up as SRID 0),
# which then breaks downstream ST_Transform, so we assign this SRS explicitly.
# Applies to OAPIF only: a WFS serves whatever srsName was negotiated (often a
# projected CRS), and -a_srs relabels without reprojecting.
DEFAULT_OGC_SRS = "EPSG:4326"

# PostgreSQL caps identifiers at 63 chars. PostGIS auto-creates a spatial index
# named `idx_<table>_<geom_col>`, so any table written via to_postgis must leave
# room for that suffix or the index creation fails mid-write.
PG_IDENTIFIER_MAX_LENGTH = 63
POSTGIS_TABLE_NAME_MAX_LENGTH = (
    PG_IDENTIFIER_MAX_LENGTH - len("idx__") - len(DEFAULT_GEOMETRY_COLUMN)
)
