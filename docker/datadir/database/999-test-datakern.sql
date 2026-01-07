insert into datakern.integrity_link (data_id, metadata_id, integrity_title, integrity_owner, integrity_organization, source_import_type, staging_table_name, final_table_name, schedule, schedule_enabled, integrity_transformation)
values
    ('distributeurs', null, 'Distributeurs de documents d''urbanisme', 'admin', 'ADMIN', 'url', 'distributeurs', 'doc_urba', '*/1 * * * *', true, '{}');


create table if not exists staging.distributeurs
(
    objectid          integer not null
        primary key,
    nom_distributeur  varchar(50),
    id_station        varchar(10),
    adresse           varchar(100),
    commune           varchar(48),
    code_postal       varchar(5),
    code_insee        varchar(5),
    longitude         real,
    latitude          real,
    geom              geometry(Point, 4326),
    date_modification timestamp
);

create index if not exists distributeurs_idx
    on staging.distributeurs using gist (geom);


INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (4, 'JARDIN PUBLIC', 'HJA002', 'RUE SADI CARNOT', 'Haubourdin', '59320', '59286', 2.98868, 50.61145, 'POINT (2.98868 50.61145)', '2025-02-05 11:11:25.564000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (3, 'LOOS MAIRIE', 'LOO002', 'RUE DU MARECHAL FOCH', 'Loos', '59120', '59360', 3.01752, 50.61509, 'POINT (3.01752 50.61509)', '2025-02-05 11:11:25.564000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (2, 'RUE DE L EGLISE', 'REG002', 'RUE NATIONALE', 'Marcq-en-Barœul', '59700', '59378', 3.07566, 50.66481, 'POINT (3.07566 50.66481)', '2025-02-05 11:11:25.564000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (1, 'PALAIS DE JUSTICE', 'PJU001', 'AVENUE DU PEUPLE BELGE', 'Lille', '59000', '59350', 3.06324, 50.64234, 'POINT (3.06324 50.64234)', '2025-02-05 11:11:25.564000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (83, 'HALLUIN - HOTEL DE VILLE', 'ROH002', 'RUE MARTHE NOLLET', 'Halluin', '59250', '59279', 3.12498, 50.78256, 'POINT (3.12498 50.78256)', '2025-08-28 12:59:22.897000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (84, 'HAUBOURDIN - JARDIN PUBLIC', 'HJA002', 'RUE SADI CARNOT', 'Haubourdin', '59320', '59286', 2.98868, 50.61145, 'POINT (2.98868 50.61145)', '2025-08-28 12:59:22.899000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (85, 'LA MADELEINE - MAIRIE', 'MLA002', '165 RUE DU GENERAL DE GAULLE', 'La Madeleine', '59110', '59368', 3.07358, 50.65486, 'POINT (3.07358 50.65486)', '2025-08-28 12:59:22.899000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (88, 'MARCQ -  RUE DE L''EGLISE', 'REG002', 'RUE NATIONALE', 'Marcq-en-Barœul', '59700', '59378', 3.07563, 50.66481, 'POINT (3.07563 50.66481)', '2025-08-28 12:59:22.899000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (89, 'RONCHIN - MAIRIE', 'RON001', '14 RUE LAVOISIER', 'Ronchin', '59790', '59507', 3.07705, 50.60506, 'POINT (3.07705 50.60506)', '2025-08-28 12:59:22.900000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (90, 'SAINT ANDRE - FOCH', 'FOS001', 'RUE DU GÉNÉRAL LECLERC', 'Saint-André-lez-Lille', '59350', '59527', 3.05015, 50.66322, 'POINT (3.05015 50.66322)', '2025-08-28 12:59:22.899000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (92, 'WATTIGNIES - FLEMING', 'WFL001', 'AVENUE CHARLES GUILLAIN', 'Wattignies', '59139', '59648', 3.04478, 50.58859, 'POINT (3.04478 50.58859)', '2025-08-28 12:59:22.899000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (93, 'WATTRELOS - DE GAULLE', 'PLG002', 'RUE J.B LEBAS', 'Wattrelos', '59150', '59650', 3.21955, 50.70329, 'POINT (3.21955 50.70329)', '2025-08-28 12:59:22.899000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (87, 'LILLE - REPUBLIQUE BEAUX ARTS', 'REP072', 'PLACE DE LA REPUBLIQUE', 'Lille', '59000', '59350', 3.06225, 50.63201, 'POINT (3.06225 50.63201)', '2025-08-28 12:59:22.900000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (86, 'LILLE - PALAIS DE JUSTICE', 'PJU001', '13 AVENUE DU PEUPLE BELGE', 'Lille', '59000', '59350', 3.06334, 50.64228, 'POINT (3.06334 50.64228)', '2025-08-28 12:59:22.899000');
INSERT INTO staging.distributeurs (objectid, nom_distributeur, id_station, adresse, commune, code_postal, code_insee, longitude, latitude, geom, date_modification) VALUES (91, 'VILLENEUVE D''ASCQ - COMICES', 'COC011', 'RUE DES COMICES', 'Villeneuve-d''Ascq', '59650', '59009', 3.15294, 50.64118, 'POINT (3.15294 50.64118)', '2025-08-28 12:59:22.899000');
