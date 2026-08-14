"""Constants used across the data_manipulation library."""

DEFAULT_GEOMETRY_COLUMN = "geom"
DB_URI_PREFIX = "db://"

# OGC API Features / WFS downloads are requested as GeoJSON, which is always
# WGS84 lon/lat per RFC 7946. GDAL does not always stamp an SRID on the loaded
# geometry (it ends up as SRID 0), which then breaks downstream ST_Transform.
# We therefore assign this SRS explicitly when ingesting OGC services.
DEFAULT_OGC_SRS = "EPSG:4326"

# PostgreSQL caps identifiers at 63 chars. PostGIS auto-creates a spatial index
# named `idx_<table>_<geom_col>`, so any table written via to_postgis must leave
# room for that suffix or the index creation fails mid-write.
PG_IDENTIFIER_MAX_LENGTH = 63
POSTGIS_TABLE_NAME_MAX_LENGTH = (
    PG_IDENTIFIER_MAX_LENGTH - len("idx__") - len(DEFAULT_GEOMETRY_COLUMN)
)
