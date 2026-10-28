-- Historic monuments of Lille, for the source database of the docker service `sourcedb_direct_access`.
--
-- Source: base Mérimée, Ministère de la Culture, dataset "Immeubles protégés au titre des
-- Monuments Historiques" https://www.data.gouv.fr/datasets/immeubles-proteges-au-titre-des-monuments-historiques-2
-- Open Data under the Licence Ouverte / Open Licence version 2.0 (Etalab)
-- https://www.etalab.gouv.fr/licence-ouverte-open-licence
-- Data modified: extract of the Lille monuments (commune_forme_index = 'Lille') having coordinates,
-- placeholder points (e.g. POINT(3 50), outside Lille) removed; nom_long built from title + address.
-- Columns: reference, nom_court (titre_editorial_de_la_notice), nom_long, type (denomination_de_l_edifice),
-- date_construction (datation_de_l_edifice), siecle_construction (siecle_de_la_campagne_principale_de_construction).
--
-- Executed by the postgis image entrypoint only when the volume is empty.
-- To replay: docker compose rm -sf sourcedb_direct_access && docker volume rm <project>_sourcedb_direct_access_data

BEGIN;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS merimee;
DROP TABLE IF EXISTS merimee.monument;
CREATE TABLE merimee.monument (
    reference           varchar(12) PRIMARY KEY,
    nom_court           text NOT NULL,
    nom_long            text NOT NULL,
    type                text,
    date_construction   text,
    siecle_construction text,
    geom                geometry(Point, 4326) NOT NULL
);
COMMENT ON TABLE merimee.monument IS 'Monuments historiques de Lille, extrait de la base Mérimée (Ministère de la Culture), Open Data sous Licence Ouverte / Open Licence version 2.0 (Etalab)';

INSERT INTO merimee.monument VALUES ('PA00107567', 'Abbaye de Loos', 'Abbaye de Loos, 34, 36, 38, 40 rue Jean-Jacques-Rousseau ; 5 rue des Trois-Molettes, Lille', 'abbaye', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0610402, 50.6400512), 4326));
INSERT INTO merimee.monument VALUES ('PA00107568', 'Bâtiment dit la Grande Garde', 'Bâtiment dit la Grande Garde, Lille', 'corps de garde', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0638813, 50.6364050), 4326));
INSERT INTO merimee.monument VALUES ('PA00107569', 'Vieille bourse du commerce', 'Vieille bourse du commerce, place Général-de-Gaulle ; rue des Manneliers ; rue des Sept-Agaches ; place du Théâtre, Lille', 'bourse de commerce', NULL, '2e moitié 17e siècle', ST_SetSRID(ST_MakePoint(3.0642802, 50.6370459), 4326));
INSERT INTO merimee.monument VALUES ('PA00107570', 'Caserne Souham', 'Caserne Souham, rue du Vieux-Faubourg, Lille', 'caserne', NULL, '17e siècle;18e siècle', ST_SetSRID(ST_MakePoint(3.0713239, 50.6380331), 4326));
INSERT INTO merimee.monument VALUES ('PA00107571', 'Ancienne chapelle des Carmes Déchaussées', 'Ancienne chapelle des Carmes Déchaussées, rue de Thionville, Lille', 'chapelle', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0667549, 50.6434015), 4326));
INSERT INTO merimee.monument VALUES ('PA00107572', 'Chapelle Notre-Dame-de-la-Réconciliation', 'Chapelle Notre-Dame-de-la-Réconciliation, 28 rue de Canteleu, Lille', 'chapelle', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0377424, 50.6260620), 4326));
INSERT INTO merimee.monument VALUES ('PA00107573', 'Citadelle de Lille', 'Citadelle de Lille, Lille', 'citadelle', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0447956, 50.6424782), 4326));
INSERT INTO merimee.monument VALUES ('PA00107574', 'Vestiges de l''ancienne collégiale Saint-Pierre', 'Vestiges de l''ancienne collégiale Saint-Pierre, rue Alphonse-Colas ; rue des Prisons, Lille', 'collégiale', NULL, 'Moyen Age', ST_SetSRID(ST_MakePoint(3.0623263, 50.6421474), 4326));
INSERT INTO merimee.monument VALUES ('PA00107575', 'Ancien couvent des Madelonnettes', 'Ancien couvent des Madelonnettes, 39, 41 rue de la Barre, Lille', 'couvent', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0563905, 50.6384950), 4326));
INSERT INTO merimee.monument VALUES ('PA00107576', 'Ancien couvent des Minimes', 'Ancien couvent des Minimes, 17 quai du Wault ; rue de la Barre, Lille', 'couvent', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0548797, 50.6381423), 4326));
INSERT INTO merimee.monument VALUES ('PA00107577', 'Eglise Saint-André', 'Eglise Saint-André, Lille', 'église', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0539410, 50.6448008), 4326));
INSERT INTO merimee.monument VALUES ('PA00107578', 'Eglise Sainte-Catherine', 'Eglise Sainte-Catherine, Lille', 'église', NULL, '16e siècle;18e siècle', ST_SetSRID(ST_MakePoint(3.0580445, 50.6368688), 4326));
INSERT INTO merimee.monument VALUES ('PA00107579', 'Eglise Saint-Denis-d''Hellemmes', 'Eglise Saint-Denis-d''Hellemmes, Lille', 'église', NULL, NULL, ST_SetSRID(ST_MakePoint(3.1109587, 50.6281260), 4326));
INSERT INTO merimee.monument VALUES ('PA00107580', 'Eglise Saint-Etienne', 'Eglise Saint-Etienne, 47 rue de l''Hôpital-Militaire, Lille', 'église paroissiale', '1606', '1er quart 17e siècle', ST_SetSRID(ST_MakePoint(3.0596552, 50.6350963), 4326));
INSERT INTO merimee.monument VALUES ('PA00107581', 'Eglise Sainte-Marie-Madeleine', 'Eglise Sainte-Marie-Madeleine, Lille', 'église', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0631919, 50.6447948), 4326));
INSERT INTO merimee.monument VALUES ('PA00107582', 'Eglise Saint-Maurice', 'Eglise Saint-Maurice, Lille', 'église', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0675008, 50.6358790), 4326));
INSERT INTO merimee.monument VALUES ('PA00107584', 'Enseigne en pierre sculptée représentant saint Nicaise', 'Enseigne en pierre sculptée représentant saint Nicaise, rue Pierre-Mauroy ; rue Gustave-Delory, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0680289, 50.6336559), 4326));
INSERT INTO merimee.monument VALUES ('PA00107585', 'Ancien fort Saint-Sauveur', 'Ancien fort Saint-Sauveur, 20 square Ruault, Lille', 'fort', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0716891, 50.6294382), 4326));
INSERT INTO merimee.monument VALUES ('PA00107586', 'Hospice Comtesse', 'Hospice Comtesse, rue de la Monnaie ; rue Comtesse, Lille', 'hospice', '1472;1724', '2e moitié 15e siècle;2e moitié 17e siècle;1ère moitié 18e siècle', ST_SetSRID(ST_MakePoint(3.0628158, 50.6411248), 4326));
INSERT INTO merimee.monument VALUES ('PA00107587', 'Hospice Ganthois', 'Hospice Ganthois, Lille', 'hospice', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0676347, 50.6312205), 4326));
INSERT INTO merimee.monument VALUES ('PA00107588', 'Hospice général', 'Hospice général, avenue du Peuple-Belge, Lille', 'hospice', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0619689, 50.6462989), 4326));
INSERT INTO merimee.monument VALUES ('PA00107589', 'Hôpital Saint-Sauveur', 'Hôpital Saint-Sauveur, Lille', 'hôpital', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0729787, 50.6308353), 4326));
INSERT INTO merimee.monument VALUES ('PA00107590', 'Hôpital militaire Scrive, ancien collège des Jésuites', 'Hôpital militaire Scrive, ancien collège des Jésuites, rue de l''Hôpital-Militaire, Lille', 'collège;hôpital', '1606', '1er quart 17e siècle', ST_SetSRID(ST_MakePoint(3.0604884, 50.6347311), 4326));
INSERT INTO merimee.monument VALUES ('PA00107591', 'Hôtel d''Ailly-d''Aigrenont', 'Hôtel d''Ailly-d''Aigrenont, 45 rue de Roubaix, Lille', 'hôtel', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0694623, 50.6391249), 4326));
INSERT INTO merimee.monument VALUES ('PA00107592', 'Hôtel d''Avelin (Hôtel du Rectorat)', 'Hôtel d''Avelin (Hôtel du Rectorat), 22 rue Saint-Jacques, Lille', 'hôtel', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0671402, 50.6404837), 4326));
INSERT INTO merimee.monument VALUES ('PA00107593', 'Hôtel Scrive, actuellement siège de la Direction régionale des Affaires culturelles du Nord-Pas-de-Calais', 'Hôtel Scrive, actuellement siège de la Direction régionale des Affaires culturelles du Nord-Pas-de-Calais, 1 rue du Lombard ; 28 rue de Roubaix, Lille', 'hôtel;établissement administratif', NULL, 'milieu 18e siècle;19e siècle;20e siècle', ST_SetSRID(ST_MakePoint(3.0689048, 50.6383797), 4326));
INSERT INTO merimee.monument VALUES ('PA00107594', 'Hôtel Bidé de la Grandville', 'Hôtel Bidé de la Grandville, 26, 28 rue de Thionville, Lille', 'hôtel', NULL, '18e siècle;19e siècle', ST_SetSRID(ST_MakePoint(3.0653052, 50.6437731), 4326));
INSERT INTO merimee.monument VALUES ('PA00107595', 'Hôtel Cardon de Montreuil', 'Hôtel Cardon de Montreuil, 26, 28 rue Négrier, Lille', 'hôtel', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0575604, 50.6425796), 4326));
INSERT INTO merimee.monument VALUES ('PA00107596', 'Hôtel des Cariatides', 'Hôtel des Cariatides, 2 à 8 rue d''Inkermann, Lille', 'hôtel', NULL, '2e moitié 19e siècle', ST_SetSRID(ST_MakePoint(3.0601934, 50.6310055), 4326));
INSERT INTO merimee.monument VALUES ('PA00107597', 'Hôtel Castiaux', 'Hôtel Castiaux, 7 rue Demazières, Lille', 'hôtel', '1885;1887', '2e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0482369, 50.6356318), 4326));
INSERT INTO merimee.monument VALUES ('PA00107598', 'Hôtel Delbecque', 'Hôtel Delbecque, 105 boulevard de la Liberté, Lille', 'hôtel', NULL, '4e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0587272, 50.6336409), 4326));
INSERT INTO merimee.monument VALUES ('PA00107599', 'Ancien Hôtel de l''Intendance', 'Ancien Hôtel de l''Intendance, 68 rue Royale, Lille', 'intendance', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0573963, 50.6415867), 4326));
INSERT INTO merimee.monument VALUES ('PA00107600', 'Ancien Hôtel du Juge Garde des Monnaies', 'Ancien Hôtel du Juge Garde des Monnaies, 61, 63 rue de la Monnaie, Lille', 'hôtel', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0617836, 50.6411053), 4326));
INSERT INTO merimee.monument VALUES ('PA00107601', 'Hôtel de Lamissart', 'Hôtel de Lamissart, 130 rue Royale, Lille', 'hôtel', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0545467, 50.6454851), 4326));
INSERT INTO merimee.monument VALUES ('PA00107602', 'Hôtel de Madre', 'Hôtel de Madre, 23 rue de Gand ; 4 rue A-Claques, Lille', 'hôtel', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0656285, 50.6420511), 4326));
INSERT INTO merimee.monument VALUES ('PA00107603', 'Hôtel de Marchiennes', 'Hôtel de Marchiennes, 191 rue Pierre Mauroy, Lille', 'hôtel', '1626', '2e quart 17e siècle;18e siècle', ST_SetSRID(ST_MakePoint(3.0688584, 50.6324376), 4326));
INSERT INTO merimee.monument VALUES ('PA00107604', 'Ancien hôtel militaire des Bleuets', 'Ancien hôtel militaire des Bleuets, place des Bleuets, Lille', 'hôtel', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0681270, 50.6414533), 4326));
INSERT INTO merimee.monument VALUES ('PA00107605', 'Hôtel Petipas de Walle', 'Hôtel Petipas de Walle, 122 rue de l''Hôpital-Militaire, Lille', 'hôtel', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0585792, 50.6370861), 4326));
INSERT INTO merimee.monument VALUES ('PA00107606', 'Hôtel des Postes', 'Hôtel des Postes, place de la République, Lille', 'bureau de poste', NULL, '2e moitié 19e siècle', ST_SetSRID(ST_MakePoint(3.0609097, 50.6307223), 4326));
INSERT INTO merimee.monument VALUES ('PA00107607', 'Hôtel Ramery', 'Hôtel Ramery, 18 rue des Arts, Lille', 'hôtel', NULL, '19e siècle', ST_SetSRID(ST_MakePoint(3.0669316, 50.6379865), 4326));
INSERT INTO merimee.monument VALUES ('PA00107608', 'Hôtel Van der Cruisse de Waziers', 'Hôtel Van der Cruisse de Waziers, 95 rue Royale, Lille', 'hôtel', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0553465, 50.6429063), 4326));
INSERT INTO merimee.monument VALUES ('PA00107609', 'Hôtel Van Zeller', 'Hôtel Van Zeller, 3 rue Négrier, Lille', 'hôtel', NULL, '18e siècle;19e siècle', ST_SetSRID(ST_MakePoint(3.0594747, 50.6427136), 4326));
INSERT INTO merimee.monument VALUES ('PA00107610', 'Hôtel particulier', 'Hôtel particulier, 28 à 36 rue des Arts, Lille', 'hôtel', NULL, '19e siècle', ST_SetSRID(ST_MakePoint(3.0665758, 50.6383590), 4326));
INSERT INTO merimee.monument VALUES ('PA00107612', 'Hôtel particulier', 'Hôtel particulier, 9, 11 place aux Bleuets, Lille', 'hôtel', NULL, '19e siècle', ST_SetSRID(ST_MakePoint(3.0675921, 50.6412466), 4326));
INSERT INTO merimee.monument VALUES ('PA00107613', 'Hôtel particulier', 'Hôtel particulier, 52 façade de l''Esplanade, Lille', 'hôtel', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0535762, 50.6430319), 4326));
INSERT INTO merimee.monument VALUES ('PA00107614', 'Hôtel particulier', 'Hôtel particulier, 20 rue des Tours, Lille', 'hôtel', '1739', '18e siècle', ST_SetSRID(ST_MakePoint(3.0667149, 50.6413243), 4326));
INSERT INTO merimee.monument VALUES ('PA00107616', 'Immeuble', 'Immeuble, 8 rue d''Angleterre, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0610436, 50.6417325), 4326));
INSERT INTO merimee.monument VALUES ('PA00107619', 'Immeubles', 'Immeubles, 4, 6, 8, 10 rue des Arts, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0671877, 50.6378143), 4326));
INSERT INTO merimee.monument VALUES ('PA00107620', 'Immeubles', 'Immeubles, 15, 17 rue des Arts, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0664803, 50.6381790), 4326));
INSERT INTO merimee.monument VALUES ('PA00107621', 'Immeuble', 'Immeuble, 55 rue de la Barre, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0557323, 50.6384987), 4326));
INSERT INTO merimee.monument VALUES ('PA00107622', 'Immeuble', 'Immeuble, 11 rue Basse, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0629691, 50.6390177), 4326));
INSERT INTO merimee.monument VALUES ('PA00107623', 'Immeuble', 'Immeuble, 45 rue Basse, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0613259, 50.6387385), 4326));
INSERT INTO merimee.monument VALUES ('PA00107624', 'Immeubles', 'Immeubles, 1, 3, 5, 15, 17, 19 rue de la Bourse, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0633731, 50.6376290), 4326));
INSERT INTO merimee.monument VALUES ('PA00107625', 'Immeubles', 'Immeubles, 2, 10 rue de la Bourse ; rue des Trois-Couronnes, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0635758, 50.6375757), 4326));
INSERT INTO merimee.monument VALUES ('PA00107627', 'Immeuble', 'Immeuble, 11 rue du Curé-Saint-Etienne, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0623679, 50.6382303), 4326));
INSERT INTO merimee.monument VALUES ('PA00107629', 'Immeuble', 'Immeuble, 23 rue du Curé-Saint-Etienne, Lille', 'immeuble', '1716', '1er quart 18e siècle', ST_SetSRID(ST_MakePoint(3.0626772, 50.6384708), 4326));
INSERT INTO merimee.monument VALUES ('PA00107630', 'Immeubles', 'Immeubles, 4, 6, 8 rue Esquermoise, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0627451, 50.6374851), 4326));
INSERT INTO merimee.monument VALUES ('PA00107631', 'Immeubles', 'Immeubles, 5, 7 rue Esquermoise, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0625032, 50.6373224), 4326));
INSERT INTO merimee.monument VALUES ('PA00107632', 'Immeuble', 'Immeuble, 15 rue Esquermoise, Lille', 'immeuble', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0622834, 50.6375552), 4326));
INSERT INTO merimee.monument VALUES ('PA00107633', 'Immeubles', 'Immeubles, 34, 36 rue Esquermoise, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0618257, 50.6379618), 4326));
INSERT INTO merimee.monument VALUES ('PA00107634', 'Immeuble', 'Immeuble, 9 rue à Fiens, Lille', 'immeuble', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0688205, 50.6377530), 4326));
INSERT INTO merimee.monument VALUES ('PA00107635', 'Immeuble', 'Immeuble, 49 rue de Gand, Lille', 'immeuble', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0666274, 50.6428221), 4326));
INSERT INTO merimee.monument VALUES ('PA00107636', 'Immeuble', 'Immeuble, place du Général-de-Gaulle ; rue Neuve, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0637364, 50.6362568), 4326));
INSERT INTO merimee.monument VALUES ('PA00107637', 'Immeuble', 'Immeuble, 9 place du Général-de-Gaulle ; anciennement Grand-Place, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0630832, 50.6364869), 4326));
INSERT INTO merimee.monument VALUES ('PA00107638', 'Immeuble', 'Immeuble, 21 place du Général-de-Gaulle ; anciennement Grand-Place, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0629268, 50.6368483), 4326));
INSERT INTO merimee.monument VALUES ('PA00107639', 'Immeubles', 'Immeubles, 34, 44, 52 place du Général-de-Gaulle ; rue des Sept-Agaches ; rue du Petit-Paon ; rue de la Bourse, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0636359, 50.6374125), 4326));
INSERT INTO merimee.monument VALUES ('PA00107640', 'Immeuble', 'Immeuble, 1 rue Grande-Chaussée, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0637911, 50.6381890), 4326));
INSERT INTO merimee.monument VALUES ('PA00107641', 'Immeuble', 'Immeuble, 9, 11 rue Grande-Chaussée, Lille', 'immeuble', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0636670, 50.6384070), 4326));
INSERT INTO merimee.monument VALUES ('PA00107642', 'Immeuble', 'Immeuble, 58 rue Gustave-Delory, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0692139, 50.6334620), 4326));
INSERT INTO merimee.monument VALUES ('PA00107643', 'Immeuble', 'Immeuble, 41 rue de l''Hôpital-Militaire, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0607790, 50.6343470), 4326));
INSERT INTO merimee.monument VALUES ('PA00107644', 'Immeubles', 'Immeubles, 1, 3, 5, 11 rue Neuve, Lille', 'immeuble', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0639181, 50.6360165), 4326));
INSERT INTO merimee.monument VALUES ('PA00107645', 'Immeuble', 'Immeuble, 38 rue Neuve, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0645034, 50.6352034), 4326));
INSERT INTO merimee.monument VALUES ('PA00107646', 'Immeubles', 'Immeubles, 72, 74 rue Pierre Mauroy, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0665218, 50.6356117), 4326));
INSERT INTO merimee.monument VALUES ('PA00107649', 'Immeubles', 'Immeubles, 120, 122 rue Pierre Mauroy, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0675376, 50.6344831), 4326));
INSERT INTO merimee.monument VALUES ('PA00107650', 'Immeubles', 'Immeubles, 8bis rue au Peterynck, Lille', 'immeuble', '1710', '1er quart 18e siècle', ST_SetSRID(ST_MakePoint(3.0618312, 50.6412292), 4326));
INSERT INTO merimee.monument VALUES ('PA00107651', 'Immeubles', 'Immeubles, 41, 43, 45 avenue du Peuple-Belge, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0613190, 50.6455664), 4326));
INSERT INTO merimee.monument VALUES ('PA00107653', 'Immeubles', 'Immeubles, 3, 5 rue du Pont-Neuf, Lille', 'immeuble', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0606563, 50.6433973), 4326));
INSERT INTO merimee.monument VALUES ('PA00107654', 'Immeuble', 'Immeuble, 7 rue du Pont-Neuf, Lille', 'immeuble', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0606902, 50.6435162), 4326));
INSERT INTO merimee.monument VALUES ('PA00107655', 'Immeubles', 'Immeubles, 9, 11 rue du Pont-Neuf ; 12 rue de l''Entrepôt, Lille', 'immeuble', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0608181, 50.6436931), 4326));
INSERT INTO merimee.monument VALUES ('PA00107656', 'Immeuble', 'Immeuble, 39 rue de Roubaix, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0692759, 50.6387671), 4326));
INSERT INTO merimee.monument VALUES ('PA00107657', 'Immeuble', 'Immeuble, 30 rue Royale, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0581851, 50.6398337), 4326));
INSERT INTO merimee.monument VALUES ('PA00107658', 'Immeubles', 'Immeubles, 17, 19 terrasse Sainte-Catherine, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0574248, 50.6393564), 4326));
INSERT INTO merimee.monument VALUES ('PA00107659', 'Immeuble', 'Immeuble, 3 rue Saint-Genois, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0682756, 50.6355708), 4326));
INSERT INTO merimee.monument VALUES ('PA00107660', 'Immeuble', 'Immeuble, 6 rue Saint-Joseph, Lille', 'immeuble', '1665', '17e siècle', ST_SetSRID(ST_MakePoint(3.0645385, 50.6420317), 4326));
INSERT INTO merimee.monument VALUES ('PA00107661', 'Immeuble', 'Immeuble, parvis Saint-Maurice, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0679383, 50.6356528), 4326));
INSERT INTO merimee.monument VALUES ('PA00107663', 'Immeubles', 'Immeubles, 1, 3, 5, 7 rue des Sept-Agaches ; rue des Trois-Couronnes, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0641684, 50.6373208), 4326));
INSERT INTO merimee.monument VALUES ('PA00107664', 'Immeubles', 'Immeubles, 13, 13bis, 15 à 35 place du Théatre ; rue des Sept-Agaches, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0640072, 50.6375690), 4326));
INSERT INTO merimee.monument VALUES ('PA00107665', 'Immeuble, siège du Cercle Phylosophique et Culturel', 'Immeuble, siège du Cercle Phylosophique et Culturel, 2 rue Thiers, Lille', 'immeuble', NULL, '19e siècle', ST_SetSRID(ST_MakePoint(3.0592618, 50.6385154), 4326));
INSERT INTO merimee.monument VALUES ('PA00107667', 'Immeubles', 'Immeubles, 1, 1 bis (anciennement rue des Trois-Couronnes ; , 3, 5 1ter ; 15 rue du Petit-Paon, Lille', 'immeuble', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0638542, 50.6373381), 4326));
INSERT INTO merimee.monument VALUES ('PA00107668', 'Immeubles', 'Immeubles, 3, 5, 7 rue de la Vieille-Comédie ; anciennement 13, 15, 17, Lille', 'immeuble', NULL, '1ère moitié 18e siècle', ST_SetSRID(ST_MakePoint(3.0636589, 50.6353452), 4326));
INSERT INTO merimee.monument VALUES ('PA00107669', 'Magasins généraux', 'Magasins généraux, 133 rue Royale ; rue du Magasin, Lille', 'entrepôt public', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0533634, 50.6458165), 4326));
INSERT INTO merimee.monument VALUES ('PA00107670', 'Maison Coilliot et son décor intérieur', 'Maison Coilliot et son décor intérieur, 14 rue de Fleurus, Lille', 'maison', '1898;1900', '4e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0601083, 50.6269948), 4326));
INSERT INTO merimee.monument VALUES ('PA00107671', 'Maison de Gilles de la Boe, dite aussi du Bon Bouillon', 'Maison de Gilles de la Boe, dite aussi du Bon Bouillon, 27, 29 place Louise-de-Bettignies ; 1, 3 avenue du Peuple-Belge, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0645531, 50.6410811), 4326));
INSERT INTO merimee.monument VALUES ('PA00107672', 'Maison Meert', 'Maison Meert, 25, 27 rue Esquermoise, Lille', 'magasin de commerce', '1839', '2e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0619220, 50.6377532), 4326));
INSERT INTO merimee.monument VALUES ('PA00107673', 'Maison', 'Maison, 3 rue de la Barre, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0585438, 50.6388238), 4326));
INSERT INTO merimee.monument VALUES ('PA00107675', 'Maison', 'Maison, 1 place des Bleuets, Lille', 'maison', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0673115, 50.6408218), 4326));
INSERT INTO merimee.monument VALUES ('PA00107676', 'Maisons faisant partie du Rang des Arbalétriers', 'Maisons faisant partie du Rang des Arbalétriers, 2 à 14 place aux Bleuets, Lille', 'maison', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0677177, 50.6407918), 4326));
INSERT INTO merimee.monument VALUES ('PA00107677', 'Maisons', 'Maisons, 3, 5, 7 place aux Bleuets, Lille', 'maison', '1719', '1er quart 18e siècle', ST_SetSRID(ST_MakePoint(3.0674988, 50.6409961), 4326));
INSERT INTO merimee.monument VALUES ('PA00107679', 'Maison', 'Maison, 26 place aux Bleuets, Lille', 'maison', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0682018, 50.6412535), 4326));
INSERT INTO merimee.monument VALUES ('PA00107680', 'Maisons', 'Maisons, 30, 32 place aux Bleuets, Lille', 'maison', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0681424, 50.6417249), 4326));
INSERT INTO merimee.monument VALUES ('PA00107681', 'Maison', 'Maison, 23 rue de la Bourse, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0636191, 50.6380381), 4326));
INSERT INTO merimee.monument VALUES ('PA00107683', 'Maison', 'Maison, 13 rue des Fossés, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0631266, 50.6346193), 4326));
INSERT INTO merimee.monument VALUES ('PA00107684', 'Maison', 'Maison, 29 rue de Gand ; rue des Célestines, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0661302, 50.6423353), 4326));
INSERT INTO merimee.monument VALUES ('PA00107685', 'Maison', 'Maison, 35 rue de Gand, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0661963, 50.6424031), 4326));
INSERT INTO merimee.monument VALUES ('PA00107686', 'Maison', 'Maison, 41 rue de Gand, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0664036, 50.6425969), 4326));
INSERT INTO merimee.monument VALUES ('PA00107687', 'Maison', 'Maison, 2, 3 place Genevières, Lille', 'maison', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0395405, 50.6238435), 4326));
INSERT INTO merimee.monument VALUES ('PA00107688', 'Maisons', 'Maisons, 4, 6 rue Grande-Chaussée, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0641077, 50.6381895), 4326));
INSERT INTO merimee.monument VALUES ('PA00107689', 'Maison', 'Maison, 14 rue Grande-Chaussée, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0641974, 50.6383170), 4326));
INSERT INTO merimee.monument VALUES ('PA00107690', 'Maisons', 'Maisons, 69, 71 rue de l''Hôpital-Militaire, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0591415, 50.6360055), 4326));
INSERT INTO merimee.monument VALUES ('PA00107691', 'Maison', 'Maison, 104 rue de l''Hôpital-Militaire, Lille', 'maison', NULL, '19e siècle', ST_SetSRID(ST_MakePoint(3.0591538, 50.6363100), 4326));
INSERT INTO merimee.monument VALUES ('PA00107692', 'Maison', 'Maison, 1 rue Lepelletier, Lille', 'maison', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0634771, 50.6380621), 4326));
INSERT INTO merimee.monument VALUES ('PA00107693', 'Maison', 'Maison, 3 rue Lepelletier, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0635411, 50.6380861), 4326));
INSERT INTO merimee.monument VALUES ('PA00107694', 'Maison', 'Maison, 5 rue Lepelletier, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0634754, 50.6381133), 4326));
INSERT INTO merimee.monument VALUES ('PA00107696', 'Maison', 'Maison, 13 place Louise-de-Bettignies, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0642664, 50.6407174), 4326));
INSERT INTO merimee.monument VALUES ('PA00107698', 'Maison', 'Maison, 12 rue des Manneliers, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0647799, 50.6368146), 4326));
INSERT INTO merimee.monument VALUES ('PA00107700', 'Maison', 'Maison, 13 rue du Nouveau-Siècle ; 110, 116 rue de l''Hôpital-Militaire, Lille', 'maison', NULL, '17e siècle;18e siècle', ST_SetSRID(ST_MakePoint(3.0594842, 50.6368831), 4326));
INSERT INTO merimee.monument VALUES ('PA00107701', 'Maison', 'Maison, 21 rue du Nouveau-Siècle, Lille', 'maison', NULL, '17e siècle;18e siècle', ST_SetSRID(ST_MakePoint(3.0593231, 50.6370786), 4326));
INSERT INTO merimee.monument VALUES ('PA00107703', 'Maison', 'Maison, 34 rue Pierre Mauroy, Lille', 'maison', NULL, '4e quart 17e siècle', ST_SetSRID(ST_MakePoint(3.0653271, 50.6364776), 4326));
INSERT INTO merimee.monument VALUES ('PA00107706', 'Maisons', 'Maisons, 13 rue du Pont-Neuf, Lille', 'maison', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0613946, 50.6437022), 4326));
INSERT INTO merimee.monument VALUES ('PA00107707', 'Maison', 'Maison, 15 rue du Pont-Neuf, Lille', 'maison', NULL, '18e siècle', ST_SetSRID(ST_MakePoint(3.0615897, 50.6438311), 4326));
INSERT INTO merimee.monument VALUES ('PA00107708', 'Maison', 'Maison, 7 rue Princesse, Lille', 'maison', NULL, '19e siècle', ST_SetSRID(ST_MakePoint(3.0589110, 50.6459834), 4326));
INSERT INTO merimee.monument VALUES ('PA00107709', 'Maisons', 'Maisons, 2, 4, 6, 8, 10, 12, 18, 20, 22, 24 place Rihour, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0631785, 50.6362774), 4326));
INSERT INTO merimee.monument VALUES ('PA00107710', 'Maison dite des Vieux Hommes', 'Maison dite des Vieux Hommes, 49 rue de Roubaix, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0702518, 50.6392907), 4326));
INSERT INTO merimee.monument VALUES ('PA00107711', 'Maison', 'Maison, 1bis rue Royale, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0584957, 50.6390552), 4326));
INSERT INTO merimee.monument VALUES ('PA00107714', 'Maison', 'Maison, 60 rue Saint-Etienne, Lille', 'maison', NULL, '17e siècle;18e siècle', ST_SetSRID(ST_MakePoint(3.0598424, 50.6364415), 4326));
INSERT INTO merimee.monument VALUES ('PA00107715', 'Maison', 'Maison, 62 rue Saint-Etienne, Lille', 'maison', NULL, '17e siècle;18e siècle', ST_SetSRID(ST_MakePoint(3.0598313, 50.6363525), 4326));
INSERT INTO merimee.monument VALUES ('PA00107716', 'Maison', 'Maison, 8 rue des Tours ; square Lestiboudois, Lille', 'maison', NULL, '16e siècle;17e siècle', ST_SetSRID(ST_MakePoint(3.0660913, 50.6407748), 4326));
INSERT INTO merimee.monument VALUES ('PA00107717', 'Maisons', 'Maisons, 2 à 8 rue des Urbanistes ; rue des Canonniers, Lille', 'maison', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0684036, 50.6408775), 4326));
INSERT INTO merimee.monument VALUES ('PA00107718', 'Maisons', 'Maisons, 9, 11, 13, 15, 17 place du Vieux-Marché ; 150 rue du Molinel, Lille', 'maison', NULL, '1ère moitié 17e siècle', ST_SetSRID(ST_MakePoint(3.0634992, 50.6327189), 4326));
INSERT INTO merimee.monument VALUES ('PA00107719', 'Palais des Beaux-Arts', 'Palais des Beaux-Arts, place de la République, Lille', 'musée', '1892', '4e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0628110, 50.6304582), 4326));
INSERT INTO merimee.monument VALUES ('PA00107720', 'Palais Rameau', 'Palais Rameau, 39 boulevard Vauban, Lille', 'pavillon d''exposition', '1875;1953', '2e moitié 19e siècle', ST_SetSRID(ST_MakePoint(3.0499608, 50.6342959), 4326));
INSERT INTO merimee.monument VALUES ('PA00107721', 'Palais Rihour', 'Palais Rihour, Lille', 'palais', NULL, 'Moyen Age', ST_SetSRID(ST_MakePoint(3.0619490, 50.6355319), 4326));
INSERT INTO merimee.monument VALUES ('PA00107722', 'Porte de Gand et ensemble des fortifications', 'Porte de Gand et ensemble des fortifications, Lille', 'ensemble fortifié', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0679965, 50.6437518), 4326));
INSERT INTO merimee.monument VALUES ('PA00107723', 'Porte de Paris', 'Porte de Paris, Lille', 'porte de ville', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0688055, 50.6296242), 4326));
INSERT INTO merimee.monument VALUES ('PA00107724', 'Porte de Roubaix', 'Porte de Roubaix, Lille', 'porte de ville', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0706899, 50.6393194), 4326));
INSERT INTO merimee.monument VALUES ('PA00107725', 'Préfecture', 'Préfecture, place de la République, Lille', 'préfecture', NULL, '2e moitié 19e siècle', ST_SetSRID(ST_MakePoint(3.0602947, 50.6321923), 4326));
INSERT INTO merimee.monument VALUES ('PA00107728', 'La Noble Tour', 'La Noble Tour, Lille', 'édifice fortifié', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0742245, 50.6308578), 4326));
INSERT INTO merimee.monument VALUES ('PA00107902', 'Ancien hôtel particulier', 'Ancien hôtel particulier, 19 rue de Roubaix, Lille', 'hôtel', '1745', '1ère moitié 18e siècle', ST_SetSRID(ST_MakePoint(3.0682088, 50.6383009), 4326));
INSERT INTO merimee.monument VALUES ('PA00107903', 'Immeuble dénommé Bains Lillois', 'Immeuble dénommé Bains Lillois, 219 boulevard de la Liberté, Lille', 'immeuble', '1892', '4e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0675140, 50.6288023), 4326));
INSERT INTO merimee.monument VALUES ('PA00107904', 'Maison natale du Général de Gaulle, actuellement musée', 'Maison natale du Général de Gaulle, actuellement musée, 9 rue Princesse, Lille', 'maison', NULL, '18e siècle;19e siècle', ST_SetSRID(ST_MakePoint(3.0587451, 50.6458537), 4326));
INSERT INTO merimee.monument VALUES ('PA00107905', 'Maison', 'Maison, 12 rue des Tours, Lille', 'maison', '1714', '1er quart 18e siècle', ST_SetSRID(ST_MakePoint(3.0659480, 50.6409188), 4326));
INSERT INTO merimee.monument VALUES ('PA00107912', 'Immeuble', 'Immeuble, 50 rue Gustave-Delory ; anciennement 42, 44, 46, Lille', 'immeuble', NULL, '2e moitié 18e siècle', ST_SetSRID(ST_MakePoint(3.0685884, 50.6334866), 4326));
INSERT INTO merimee.monument VALUES ('PA00107913', 'Maison', 'Maison, 77 rue de la Barre, Lille', 'maison', NULL, '1ère moitié 17e siècle', ST_SetSRID(ST_MakePoint(3.0544615, 50.6383853), 4326));
INSERT INTO merimee.monument VALUES ('PA00107915', 'Hôtel particulier (hôtel de Tenremonde)', 'Hôtel particulier (hôtel de Tenremonde), 18 rue Jean-Moulin ; anciennement rue des Marais, Lille', 'hôtel', NULL, '17e siècle;4e quart 18e siècle', ST_SetSRID(ST_MakePoint(3.0590328, 50.6417008), 4326));
INSERT INTO merimee.monument VALUES ('PA00107916', 'Maison en pans de bois', 'Maison en pans de bois, 39 rue de la Monnaie, Lille', 'maison', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0628113, 50.6408014), 4326));
INSERT INTO merimee.monument VALUES ('PA00125622', 'Maison', 'Maison, 2 place de l''Arsenal, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0582199, 50.6374510), 4326));
INSERT INTO merimee.monument VALUES ('PA00125623', 'Maison', 'Maison, 4-6 place de l''Arsenal, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0580979, 50.6374765), 4326));
INSERT INTO merimee.monument VALUES ('PA00125624', 'Maison', 'Maison, 8 place de l''Arsenal, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0580194, 50.6374429), 4326));
INSERT INTO merimee.monument VALUES ('PA00125625', 'Maison', 'Maison, 4 rue de la Baignerie, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0578325, 50.6374355), 4326));
INSERT INTO merimee.monument VALUES ('PA00125626', 'Maison', 'Maison, 38 rue de la Baignerie, Lille', 'maison', '1717', '1er quart 18e siècle', ST_SetSRID(ST_MakePoint(3.0565696, 50.6371854), 4326));
INSERT INTO merimee.monument VALUES ('PA00125627', 'Maison', 'Maison, 40 rue des Bouchers, Lille', 'maison', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0581693, 50.6375374), 4326));
INSERT INTO merimee.monument VALUES ('PA00125628', 'Maison', 'Maison, 1, 1bis rue de la Halloterie, Lille', 'maison', '1717', '1er quart 18e siècle', ST_SetSRID(ST_MakePoint(3.0566371, 50.6372116), 4326));
INSERT INTO merimee.monument VALUES ('PA00125629', 'Maison', 'Maison, 12 rue Saint-François, Lille', 'maison', '1658', '17e siècle', ST_SetSRID(ST_MakePoint(3.0635952, 50.6441774), 4326));
INSERT INTO merimee.monument VALUES ('PA00125630', 'Maison', 'Maison, 14 rue Saint-François, Lille', 'maison', '1658', '17e siècle', ST_SetSRID(ST_MakePoint(3.0636950, 50.6441983), 4326));
INSERT INTO merimee.monument VALUES ('PA00125631', 'Ancien canal de la Baignerie', 'Ancien canal de la Baignerie, Lille', 'canal', NULL, NULL, ST_SetSRID(ST_MakePoint(3.0579190, 50.6375309), 4326));
INSERT INTO merimee.monument VALUES ('PA00135486', 'Hôtel particulier', 'Hôtel particulier, 15 rue de la Barre, Lille', 'hôtel', NULL, '2e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0578967, 50.6386435), 4326));
INSERT INTO merimee.monument VALUES ('PA00135487', 'Immeuble', 'Immeuble, 30 rue de Gand, Lille', 'immeuble', NULL, '2e moitié 18e siècle', ST_SetSRID(ST_MakePoint(3.0659815, 50.6418544), 4326));
INSERT INTO merimee.monument VALUES ('PA00135488', 'Immeuble', 'Immeuble, 31 rue de Gand, Lille', 'immeuble', NULL, '17e siècle', ST_SetSRID(ST_MakePoint(3.0660734, 50.6422781), 4326));
INSERT INTO merimee.monument VALUES ('PA59000002', 'Maison de fond de cour', 'Maison de fond de cour, 64 rue Princesse, Lille', 'maison', '1677', '2e moitié 17e siècle', ST_SetSRID(ST_MakePoint(3.0560579, 50.6453809), 4326));
INSERT INTO merimee.monument VALUES ('PA59000003', 'Immeuble', 'Immeuble, 10 rue des Tours, Lille', 'immeuble', NULL, '16e siècle', ST_SetSRID(ST_MakePoint(3.0660519, 50.6408221), 4326));
INSERT INTO merimee.monument VALUES ('PA59000008', 'Ecole Nationale Supérieure des Arts et Métiers', 'Ecole Nationale Supérieure des Arts et Métiers, boulevard Louis-XIV ; rue Kléber ; rue Camille-Guérin ; rue du Professeur-Calmette, Lille', 'école supérieure;école professionnelle', '1886', '4e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0712486, 50.6280996), 4326));
INSERT INTO merimee.monument VALUES ('PA59000009', 'Jardin des Plantes', 'Jardin des Plantes, rue du Jardin-des-Plantes, Lille', 'jardin botanique', NULL, '1ère moitié 20e siècle', ST_SetSRID(ST_MakePoint(3.0677032, 50.6148741), 4326));
INSERT INTO merimee.monument VALUES ('PA59000010', 'Lycée Baggio, anciennement dénommé Institut Diderot', 'Lycée Baggio, anciennement dénommé Institut Diderot, boulevard des Défenseurs ; boulevard d''Alsace, Lille', 'lycée', '1934', '2e quart 20e siècle', ST_SetSRID(ST_MakePoint(3.0670803, 50.6168574), 4326));
INSERT INTO merimee.monument VALUES ('PA59000043', 'Opéra de Lille', 'Opéra de Lille, place du Théâtre, Lille', 'opéra', '1907', '1er quart 20e siècle', ST_SetSRID(ST_MakePoint(3.0653173, 50.6377194), 4326));
INSERT INTO merimee.monument VALUES ('PA59000044', 'Usine élévatoire de Saint-André', 'Usine élévatoire de Saint-André, 2 rue Ampère, Lille', 'établissement élévateur des eaux', '1876;1896', '4e quart 19e siècle;1er quart 20e siècle', ST_SetSRID(ST_MakePoint(3.0599126, 50.6485693), 4326));
INSERT INTO merimee.monument VALUES ('PA59000062', 'Salle des fêtes, à Lille-Fives', 'Salle des fêtes, à Lille-Fives, 91 rue de Lannoy, Lille', 'salle des fêtes', '1925', '2e quart 20e siècle', ST_SetSRID(ST_MakePoint(3.0953899, 50.6342446), 4326));
INSERT INTO merimee.monument VALUES ('PA59000078', 'Hôtel de ville', 'Hôtel de ville, place Roger-Salengro ; place Augustin-Laurent ; rue du Réduit ; rue Saint-Sauveur, Lille', 'hôtel de ville', '1920;1932', '1ère moitié 20e siècle', ST_SetSRID(ST_MakePoint(3.0711316, 50.6303019), 4326));
INSERT INTO merimee.monument VALUES ('PA59000079', 'Observatoire de l''Institut de mathématiques appliquées et d''astronomie', 'Observatoire de l''Institut de mathématiques appliquées et d''astronomie, impasse de l''Observatoire, Lille', 'observatoire', '1932', '2e quart 20e siècle', ST_SetSRID(ST_MakePoint(3.0714730, 50.6151338), 4326));
INSERT INTO merimee.monument VALUES ('PA59000107', 'Porte de Dunkerque', 'Porte de Dunkerque, avenue Léon-Jouhaux, Lille', 'porte de ville', NULL, '19e siècle', ST_SetSRID(ST_MakePoint(3.0412980, 50.6367825), 4326));
INSERT INTO merimee.monument VALUES ('PA59000112', 'Immeuble', 'Immeuble, 15 place Richebé, Lille', 'immeuble', NULL, '4e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0623312, 50.6317017), 4326));
INSERT INTO merimee.monument VALUES ('PA59000126', 'Chapelle de la famille Gonnet, située au cimetière de l''Est', 'Chapelle de la famille Gonnet, située au cimetière de l''Est, Lille', 'chapelle funéraire', '1858', '3e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0810083, 50.6435318), 4326));
INSERT INTO merimee.monument VALUES ('PA59000140', 'Maison', 'Maison, 16 rue Basse, Lille', 'maison', NULL, 'limite 16e siècle 17e siècle', ST_SetSRID(ST_MakePoint(3.0632089, 50.6392336), 4326));
INSERT INTO merimee.monument VALUES ('PA59000146', 'Cathédrale Notre-Dame de la Treille', 'Cathédrale Notre-Dame de la Treille, parvis de la Treille, Lille', 'cathédrale', '1854', '3e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0628142, 50.6401840), 4326));
INSERT INTO merimee.monument VALUES ('PA59000147', 'Maison', 'Maison, 32-32bis rue d''Antin, Lille', 'maison', '1909', '1er quart 20e siècle', ST_SetSRID(ST_MakePoint(3.0459332, 50.6278666), 4326));
INSERT INTO merimee.monument VALUES ('PA59000172', 'Temple protestant', 'Temple protestant, 15 rue Jeanne-d''Arc ; place du Temple ; rue Auguste-Angellier, Lille', 'temple', '1868', '3e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0650355, 50.6282862), 4326));
INSERT INTO merimee.monument VALUES ('PA59000177', 'Maison', 'Maison, 32 rue Vantroyen, Lille', 'maison', '1862', '3e quart 19e siècle', ST_SetSRID(ST_MakePoint(3.0847248, 50.6401099), 4326));
INSERT INTO merimee.monument VALUES ('PA59000184', 'Hôtel Catel-Béghin', 'Hôtel Catel-Béghin, 19bis-21 boulevard de la Liberté, Lille', 'hôtel', '1877', '2e moitié 19e siècle', ST_SetSRID(ST_MakePoint(3.0533738, 50.6368055), 4326));
INSERT INTO merimee.monument VALUES ('PA59000185', 'Ancien siège social de la Société des Mines de Lens', 'Ancien siège social de la Société des Mines de Lens, 30 rue Thiers ; 25 rue des Bouchers, Lille', 'mine;bâtiment administratif d''entreprise', '1903', '1er quart 20e siècle', ST_SetSRID(ST_MakePoint(3.0586987, 50.6379285), 4326));
INSERT INTO merimee.monument VALUES ('PA59000190', 'Eglise Notre-Dame de Fives', 'Eglise Notre-Dame de Fives, place du Prieuré, Lille', 'église', '1852', '19e siècle', ST_SetSRID(ST_MakePoint(3.0879665, 50.6342026), 4326));
INSERT INTO merimee.monument VALUES ('PA59000191', 'Chambre de Commerce et d''Industrie', 'Chambre de Commerce et d''Industrie, place du Théâtre, Lille', 'bourse de commerce', '1910', '20e siècle', ST_SetSRID(ST_MakePoint(3.0644428, 50.6379554), 4326));
INSERT INTO merimee.monument VALUES ('PA59000192', 'Poissonnerie A l''Huîtrière', 'Poissonnerie A l''Huîtrière, 3-7 rue des Chats-Bossus, Lille', 'magasin de commerce', '1928;1940', '20e siècle', ST_SetSRID(ST_MakePoint(3.0638932, 50.6394946), 4326));

CREATE INDEX monument_geom_idx ON merimee.monument USING gist (geom);
COMMIT;
