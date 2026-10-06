-- Fake table in the geocontrib_opendata schema, next to the views of 03-geocontrib_opendata.sql:
-- same columns as the geocontrib views, but a real table (primary key, typed geometry, clean
-- date column) to compare table vs view imports.

CREATE TABLE geocontrib_opendata.signalements_factices (
    feature_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title varchar(128) NOT NULL,
    description text,
    geom geometry(Point, 4326) NOT NULL,
    project_id integer NOT NULL,
    feature_type_id integer NOT NULL,
    status varchar(50) NOT NULL,
    thematique text,
    gestionnaire text,
    echeance date,
    created_on timestamptz NOT NULL
);

INSERT INTO geocontrib_opendata.signalements_factices
    (title, description, geom, project_id, feature_type_id, status, thematique, gestionnaire, echeance, created_on)
SELECT
    'Signalement factice n°' || i,
    CASE WHEN i % 4 = 0 THEN NULL ELSE 'Description factice du signalement n°' || i END,
    ST_SetSRID(ST_MakePoint(3.00 + random() * 0.15, 50.58 + random() * 0.10), 4326),
    999,
    9999,
    (ARRAY['draft', 'pending', 'published', 'archived'])[1 + i % 4],
    (ARRAY['Propreté', 'Entretien', 'Travaux', 'Tranquillité', 'Concertation'])[1 + i % 5],
    (ARRAY['Ville', 'MEL', 'Bailleur A', 'Bailleur B', NULL])[1 + i % 5],
    CASE WHEN i % 3 = 0 THEN NULL ELSE date '2026-01-01' + i END,
    timestamptz '2025-06-01' + (i || ' hours')::interval
FROM generate_series(1, 200) AS i;

CREATE INDEX ON geocontrib_opendata.signalements_factices USING gist (geom);
