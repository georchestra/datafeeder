CREATE TABLE geonetwork.categories (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

ALTER TABLE geonetwork.categories OWNER TO georchestra;

COPY geonetwork.categories (id, name) FROM stdin;
100	geonetwork-ui:IS_REFERENCE_DATASET
\.

ALTER TABLE ONLY geonetwork.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


CREATE TABLE geonetwork.categoriesdes (
    iddes integer NOT NULL,
    label character varying(255) NOT NULL,
    langid character varying(5) NOT NULL
);

ALTER TABLE geonetwork.categoriesdes OWNER TO georchestra;

COPY geonetwork.categoriesdes (iddes, label, langid) FROM stdin;
100	geonetwork-ui:IS_REFERENCE_DATASET	swe
100	geonetwork-ui:IS_REFERENCE_DATASET	dut
100	geonetwork-ui:IS_REFERENCE_DATASET	chi
100	geonetwork-ui:IS_REFERENCE_DATASET	spa
100	geonetwork-ui:IS_REFERENCE_DATASET	fin
100	geonetwork-ui:IS_REFERENCE_DATASET	rum
100	geonetwork-ui:IS_REFERENCE_DATASET	pol
100	geonetwork-ui:IS_REFERENCE_DATASET	aze
100	geonetwork-ui:IS_REFERENCE_DATASET	dan
100	geonetwork-ui:IS_REFERENCE_DATASET	geo
100	geonetwork-ui:IS_REFERENCE_DATASET	nor
100	geonetwork-ui:IS_REFERENCE_DATASET	tur
100	geonetwork-ui:IS_REFERENCE_DATASET	ara
100	geonetwork-ui:IS_REFERENCE_DATASET	rus
100	geonetwork-ui:IS_REFERENCE_DATASET	por
100	geonetwork-ui:IS_REFERENCE_DATASET	ger
100	geonetwork-ui:IS_REFERENCE_DATASET	cat
100	geonetwork-ui:IS_REFERENCE_DATASET	ita
100	geonetwork-ui:IS_REFERENCE_DATASET	slo
100	geonetwork-ui:IS_REFERENCE_DATASET	fre
100	geonetwork-ui:IS_REFERENCE_DATASET	arm
100	geonetwork-ui:IS_REFERENCE_DATASET	ukr
100	geonetwork-ui:IS_REFERENCE_DATASET	eng
100	geonetwork-ui:IS_REFERENCE_DATASET	wel
\.

ALTER TABLE ONLY geonetwork.categoriesdes
    ADD CONSTRAINT fkso3adnjy8lpuw1fvpdws0o36n FOREIGN KEY (iddes) REFERENCES geonetwork.categories(id);
