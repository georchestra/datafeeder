-- Fake datasets for the SOURCE_DB_2 source database (docker service `sourcedb`).
--
-- Executed by the postgis image entrypoint only when the volume is empty.
-- To replay: docker compose rm -sf sourcedb && docker volume rm <project>_sourcedb_data
-- A real dump can be dropped next to this file (e.g. 02-dump.sql), scripts run in alphabetical order.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS referentiel;

-- Points, WGS84, mixed attribute types and NULLs
CREATE TABLE geo.stations_mesure (
    id serial PRIMARY KEY,
    code varchar(10) NOT NULL UNIQUE,
    nom text NOT NULL,
    type_station text,
    altitude_m numeric(6, 1),
    active boolean NOT NULL DEFAULT true,
    date_mise_service date,
    derniere_mesure timestamptz,
    attributs jsonb,
    geom geometry(Point, 4326) NOT NULL
);

INSERT INTO geo.stations_mesure (code, nom, type_station, altitude_m, active, date_mise_service, derniere_mesure, attributs, geom)
SELECT
    'ST' || lpad(i::text, 4, '0'),
    'Station n°' || i || ' – ' || (ARRAY['Lyon', 'Grenoble', 'Chambéry', 'Annecy', 'Saint-Étienne'])[1 + i % 5],
    (ARRAY['météo', 'hydrométrie', 'qualité de l''air', NULL])[1 + i % 4],
    round((200 + random() * 1800)::numeric, 1),
    i % 7 <> 0,
    date '2000-01-01' + (i * 37),
    CASE WHEN i % 5 = 0 THEN NULL ELSE now() - (i || ' hours')::interval END,
    jsonb_build_object('capteurs', i % 4 + 1, 'operateur', 'Opérateur ' || (i % 3 + 1)),
    ST_SetSRID(ST_MakePoint(4.5 + random() * 2.5, 44.8 + random() * 1.6), 4326)
FROM generate_series(1, 250) AS i;

-- Lines, Lambert 93
CREATE TABLE geo.troncons_cours_eau (
    id bigserial PRIMARY KEY,
    nom_cours_eau text,
    classe smallint CHECK (classe BETWEEN 1 AND 5),
    longueur_m double precision,
    geom geometry(LineString, 2154) NOT NULL
);

INSERT INTO geo.troncons_cours_eau (nom_cours_eau, classe, geom)
SELECT
    (ARRAY['Rhône', 'Isère', 'Drac', 'Arve', 'Saône', NULL])[1 + i % 6],
    1 + i % 5,
    ST_SetSRID(ST_MakeLine(ARRAY[
        ST_MakePoint(x0, y0),
        ST_MakePoint(x0 + 500 + random() * 1500, y0 + random() * 1000),
        ST_MakePoint(x0 + 1500 + random() * 2500, y0 + 500 + random() * 1500)
    ]), 2154)
FROM (
    SELECT i, 830000 + random() * 150000 AS x0, 6440000 + random() * 200000 AS y0
    FROM generate_series(1, 500) AS i
) s;

UPDATE geo.troncons_cours_eau SET longueur_m = ST_Length(geom);

-- MultiPolygons, Lambert 93
CREATE TABLE geo.parcelles (
    id serial PRIMARY KEY,
    idu char(14) NOT NULL UNIQUE,
    commune_insee char(5) NOT NULL,
    section varchar(2),
    numero integer,
    surface_m2 double precision,
    geom geometry(MultiPolygon, 2154) NOT NULL
);

INSERT INTO geo.parcelles (idu, commune_insee, section, numero, geom)
SELECT
    insee || '000' || sect || lpad(i::text, 4, '0'),
    insee,
    sect,
    i,
    ST_Multi(ST_MakeEnvelope(x0, y0, x0 + 20 + random() * 80, y0 + 20 + random() * 80, 2154))
FROM (
    SELECT
        i,
        (ARRAY['69123', '38185', '73065', '74010'])[1 + i % 4] AS insee,
        (ARRAY['AB', 'AC', 'ZK'])[1 + i % 3] AS sect,
        840000 + (i % 40) * 110 AS x0,
        6510000 + (i / 40) * 110 AS y0
    FROM generate_series(1, 1000) AS i
) s;

UPDATE geo.parcelles SET surface_m2 = ST_Area(geom);

-- Table without primary key and with a generic geometry column (mixed types)
CREATE TABLE geo.objets_divers (
    libelle text,
    geom geometry(Geometry, 4326)
);

INSERT INTO geo.objets_divers (libelle, geom) VALUES
    ('Point isolé', ST_GeomFromText('POINT(5.72 45.19)', 4326)),
    ('Ligne', ST_GeomFromText('LINESTRING(5.70 45.18, 5.75 45.20)', 4326)),
    ('Polygone', ST_GeomFromText('POLYGON((5.70 45.18, 5.71 45.18, 5.71 45.19, 5.70 45.19, 5.70 45.18))', 4326)),
    ('Sans géométrie', NULL);

-- Non-spatial reference table
CREATE TABLE referentiel.communes (
    insee char(5) PRIMARY KEY,
    nom text NOT NULL,
    departement char(2) NOT NULL,
    population integer
);

INSERT INTO referentiel.communes VALUES
    ('69123', 'Lyon', '69', 522250),
    ('38185', 'Grenoble', '38', 158198),
    ('73065', 'Chambéry', '73', 59856),
    ('74010', 'Annecy', '74', 130721);

-- View joining spatial and non-spatial data
CREATE VIEW geo.v_parcelles_communes AS
SELECT p.id, p.idu, c.nom AS commune, c.departement, p.surface_m2, p.geom
FROM geo.parcelles p
JOIN referentiel.communes c ON c.insee = p.commune_insee;

CREATE INDEX ON geo.stations_mesure USING gist (geom);
CREATE INDEX ON geo.troncons_cours_eau USING gist (geom);
CREATE INDEX ON geo.parcelles USING gist (geom);
