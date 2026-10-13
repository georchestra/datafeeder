-- Read-only user on the merimee schema, for the source database of the docker service
-- `sourcedb_direct_access` (e.g. for a GeoServer datastore reading the tables in place).
--
-- Executed by the postgis image entrypoint only when the volume is empty, after 05-merimee_monument.sql.

BEGIN;
CREATE ROLE patrimoine_reader LOGIN PASSWORD 'patrimoine_reader_password';
GRANT CONNECT ON DATABASE patrimoine TO patrimoine_reader;
GRANT USAGE ON SCHEMA merimee TO patrimoine_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA merimee TO patrimoine_reader;
-- Tables created later in merimee by the owner are readable too
ALTER DEFAULT PRIVILEGES IN SCHEMA merimee GRANT SELECT ON TABLES TO patrimoine_reader;
-- GeoServer reads geometry_columns / spatial_ref_sys in public
GRANT USAGE ON SCHEMA public TO patrimoine_reader;
COMMIT;
