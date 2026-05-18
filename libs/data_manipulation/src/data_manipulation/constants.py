"""Constants used across the data_manipulation library."""

DEFAULT_GEOMETRY_COLUMN = "geom"
DB_URI_PREFIX = "db://"

# PostgreSQL caps identifiers at 63 chars. PostGIS auto-creates a spatial index
# named `idx_<table>_<geom_col>`, so any table written via to_postgis must leave
# room for that suffix or the index creation fails mid-write.
PG_IDENTIFIER_MAX_LENGTH = 63
POSTGIS_TABLE_NAME_MAX_LENGTH = PG_IDENTIFIER_MAX_LENGTH - len("idx__") - len(DEFAULT_GEOMETRY_COLUMN)
