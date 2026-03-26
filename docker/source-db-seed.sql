-- Seed script for the external source database (database import type)
-- Creates a schema with sample geospatial data for local development

CREATE SCHEMA IF NOT EXISTS source_data;

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS source_data.sample_points (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(63),
    description TEXT,
    geom geometry(Point, 4326)
);

INSERT INTO source_data.sample_points (name, category, description, geom)
VALUES
    ('Lille City Hall', 'public_building', 'Main city hall of Lille', ST_SetSRID(ST_MakePoint(3.0573, 50.6292), 4326)),
    ('Parc de la Citadelle', 'park', 'Large urban park in Lille', ST_SetSRID(ST_MakePoint(3.0445, 50.6378), 4326)),
    ('Gare Lille Flandres', 'transport', 'Main railway station', ST_SetSRID(ST_MakePoint(3.0700, 50.6365), 4326)),
    ('Grand Place', 'public_space', 'Central square of Lille', ST_SetSRID(ST_MakePoint(3.0635, 50.6371), 4326)),
    ('Musee des Beaux-Arts', 'museum', 'Fine arts museum', ST_SetSRID(ST_MakePoint(3.0594, 50.6310), 4326))
ON CONFLICT DO NOTHING;
