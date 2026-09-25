--
-- Views of the geocontrib_opendata schema, from a pg_dump -n geocontrib_opendata
-- (PostgreSQL 16.15). Edited for local init: \restrict/\unrestrict and
-- "OWNER TO int_geocontrib" statements removed (that role does not exist here).
-- Only the views returning rows with the anonymised data are kept (feature types 1 and 189).
-- The underlying public.geocontrib_feature table is an anonymised copy, in 02-geocontrib_feature.sql.
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: geocontrib_opendata; Type: SCHEMA; Schema: -
--

CREATE SCHEMA geocontrib_opendata;

COMMENT ON SCHEMA geocontrib_opendata IS 'Schema created automatically by geocontrib in mode Projet';

--
-- Name: v_diagnostic_en_marchant_campagne_2025; Type: VIEW; Schema: geocontrib_opendata
--

CREATE VIEW geocontrib_opendata.v_diagnostic_en_marchant_campagne_2025 AS
 SELECT feature_id,
    title,
    description,
    geom,
    project_id,
    feature_type_id,
    status,
    (feature_data ->> 'anim'::text) AS anim,
    (feature_data ->> 'conc'::text) AS conc,
    (feature_data ->> 'createur'::text) AS createur,
    ((feature_data ->> 'echeance'::text))::date AS echeance,
    (feature_data ->> 'entr'::text) AS entr,
    (feature_data ->> 'form'::text) AS form,
    (feature_data ->> 'gestionnaire'::text) AS gestionnaire,
    (feature_data ->> 'probleme'::text) AS probleme,
    (feature_data ->> 'prop'::text) AS prop,
    (feature_data ->> 'sec'::text) AS sec,
    (feature_data ->> 'solution'::text) AS solution,
    (feature_data ->> 'thematique'::text) AS thematique,
    (feature_data ->> 'titre'::text) AS titre,
    (feature_data ->> 'tranq'::text) AS tranq,
    (feature_data ->> 'trav'::text) AS trav
   FROM public.geocontrib_feature
  WHERE ((feature_type_id = 189) AND ((status)::text = ANY ((ARRAY['draft'::character varying, 'pending'::character varying, 'published'::character varying, 'archived'::character varying])::text[])) AND (deletion_on IS NULL));

--
-- Name: v_gusp; Type: VIEW; Schema: geocontrib_opendata
--

CREATE VIEW geocontrib_opendata.v_gusp AS
 SELECT feature_id,
    title,
    description,
    geom,
    project_id,
    feature_type_id,
    status,
    (feature_data ->> 'adresse'::text) AS adresse,
    (feature_data ->> 'com-sec'::text) AS com_sec,
    (feature_data ->> 'com_ani'::text) AS com_ani,
    (feature_data ->> 'com_conce'::text) AS com_conce,
    (feature_data ->> 'com_entre'::text) AS com_entre,
    (feature_data ->> 'com_form'::text) AS com_form,
    (feature_data ->> 'com_prop'::text) AS com_prop,
    (feature_data ->> 'com_tranq'::text) AS com_tranq,
    (feature_data ->> 'com_trav'::text) AS com_trav,
    ((feature_data ->> 'echeance'::text))::date AS echeance,
    (feature_data ->> 'probleme'::text) AS probleme,
    (feature_data ->> 'proprietaire'::text) AS proprietaire,
    (feature_data ->> 'residence'::text) AS residence,
    (feature_data ->> 'solution'::text) AS solution,
    (feature_data ->> 'thematique'::text) AS thematique
   FROM public.geocontrib_feature
  WHERE ((feature_type_id = 1) AND ((status)::text = ANY ((ARRAY['draft'::character varying, 'pending'::character varying, 'published'::character varying, 'archived'::character varying])::text[])) AND (deletion_on IS NULL));

--
-- PostgreSQL database dump complete
--
