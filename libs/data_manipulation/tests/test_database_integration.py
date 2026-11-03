"""Integration tests for database utility functions, against a PostGIS container.

The container is initialized with the scripts of the docker service `sourcedb_direct_access`
(merimee.monument + the read-only user patrimoine_reader). Skipped when Docker is unavailable.
"""

from collections.abc import Iterator
from pathlib import Path

import docker
import pytest
from docker.errors import DockerException
from sqlalchemy import Engine, create_engine, text
from testcontainers.community.postgres import PostgresContainer

from data_manipulation.database import TableExtent, list_tables_by_schema, read_table_extent

pytestmark = pytest.mark.integration

INIT_SCRIPTS_DIR = Path(__file__).parents[3] / "docker" / "sourcedb_direct_access"
POSTGIS_IMAGE = "postgis/postgis:18-3.6"


def _docker_available() -> bool:
    try:
        docker.from_env().ping()
    except DockerException:
        return False
    return True


@pytest.fixture(scope="module")
def patrimoine_db() -> Iterator[PostgresContainer]:
    if not _docker_available():
        pytest.skip("Docker is not available")
    container = PostgresContainer(
        POSTGIS_IMAGE,
        username="patrimoine",
        password="patrimoine_password",
        dbname="patrimoine",
        driver="psycopg",
    ).with_volume_mapping(str(INIT_SCRIPTS_DIR), "/docker-entrypoint-initdb.d", "ro")
    with container:
        yield container


def _engine(container: PostgresContainer, user: str, password: str) -> Iterator[Engine]:
    host = container.get_container_host_ip()
    port = container.get_exposed_port(5432)
    engine = create_engine(f"postgresql+psycopg://{user}:{password}@{host}:{port}/patrimoine")
    yield engine
    engine.dispose()


@pytest.fixture
def owner_engine(patrimoine_db: PostgresContainer) -> Iterator[Engine]:
    yield from _engine(patrimoine_db, "patrimoine", "patrimoine_password")


@pytest.fixture
def reader_engine(patrimoine_db: PostgresContainer) -> Iterator[Engine]:
    yield from _engine(patrimoine_db, "patrimoine_reader", "patrimoine_reader_password")


def test_lists_monument_table_without_postgis_tables(owner_engine: Engine) -> None:
    # spatial_ref_sys, geometry_columns... belong to the postgis extension: left out
    assert list_tables_by_schema(owner_engine) == {"merimee": ["monument"]}


def test_read_only_user_sees_granted_tables(reader_engine: Engine) -> None:
    assert list_tables_by_schema(reader_engine) == {"merimee": ["monument"]}


def test_groups_and_sorts_by_schema(owner_engine: Engine) -> None:
    with owner_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA referentiel"))
        conn.execute(text("CREATE TABLE referentiel.commune (code text)"))
        conn.execute(text("CREATE VIEW merimee.eglise AS SELECT * FROM merimee.monument"))
    try:
        assert list_tables_by_schema(owner_engine) == {
            "merimee": ["eglise", "monument"],
            "referentiel": ["commune"],
        }
    finally:
        with owner_engine.begin() as conn:
            conn.execute(text("DROP SCHEMA referentiel CASCADE"))
            conn.execute(text("DROP VIEW merimee.eglise"))


def test_hides_tables_without_privilege(owner_engine: Engine, reader_engine: Engine) -> None:
    with owner_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA private"))
        conn.execute(text("CREATE TABLE private.secret (id int)"))
        conn.execute(text("CREATE TABLE public.not_granted (id int)"))
    try:
        assert list_tables_by_schema(reader_engine) == {"merimee": ["monument"]}
    finally:
        with owner_engine.begin() as conn:
            conn.execute(text("DROP SCHEMA private CASCADE"))
            conn.execute(text("DROP TABLE public.not_granted"))


@pytest.fixture
def extent_schema(owner_engine: Engine) -> Iterator[str]:
    with owner_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA extent"))
    yield "extent"
    with owner_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA extent CASCADE"))


def _create_table(engine: Engine, ddl: str, *inserts: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(ddl))
        for insert in inserts:
            conn.execute(text(insert))


def test_extent_of_monument(reader_engine: Engine) -> None:
    extent = read_table_extent(reader_engine, "merimee", "monument")

    assert extent.is_geographic
    assert extent.epsg == 4326
    # Lille
    assert 3.0 < extent.bbox["minx"] < extent.bbox["maxx"] < 3.2
    assert 50.5 < extent.bbox["miny"] < extent.bbox["maxy"] < 50.7


def test_extent_prefers_geom_column(owner_engine: Engine, extent_schema: str) -> None:
    # a_geom comes first by name, but geom is the column of the datafeeder final tables
    _create_table(
        owner_engine,
        "CREATE TABLE extent.two_geoms (a_geom geometry(Point, 2154), geom geometry(Point, 4326))",
        "INSERT INTO extent.two_geoms VALUES "
        "(ST_SetSRID(ST_MakePoint(700000, 7000000), 2154), ST_SetSRID(ST_MakePoint(3, 50), 4326)),"
        "(ST_SetSRID(ST_MakePoint(710000, 7010000), 2154), ST_SetSRID(ST_MakePoint(4, 51), 4326))",
    )

    assert read_table_extent(owner_engine, extent_schema, "two_geoms") == TableExtent(
        is_geographic=True,
        epsg=4326,
        bbox={"minx": 3.0, "miny": 50.0, "maxx": 4.0, "maxy": 51.0},
    )


def test_extent_without_geom_column_takes_first_by_name(
    owner_engine: Engine, extent_schema: str
) -> None:
    _create_table(
        owner_engine,
        'CREATE TABLE extent.other_geoms ("Z_geom" geometry(Point, 4326), '
        '"The Geom" geometry(Point, 2154))',
        "INSERT INTO extent.other_geoms VALUES "
        "(ST_SetSRID(ST_MakePoint(3, 50), 4326), ST_SetSRID(ST_MakePoint(700000, 7000000), 2154))",
    )

    assert read_table_extent(owner_engine, extent_schema, "other_geoms") == TableExtent(
        is_geographic=True,
        epsg=2154,
        bbox={"minx": 700000.0, "miny": 7000000.0, "maxx": 700000.0, "maxy": 7000000.0},
    )


def test_extent_of_untyped_geometry_reads_srid_from_data(
    owner_engine: Engine, extent_schema: str
) -> None:
    _create_table(
        owner_engine,
        "CREATE TABLE extent.untyped (geom geometry)",
        "INSERT INTO extent.untyped VALUES (ST_SetSRID(ST_MakePoint(1, 2), 3857))",
    )

    extent = read_table_extent(owner_engine, extent_schema, "untyped")

    assert extent.is_geographic
    assert extent.epsg == 3857


def test_extent_of_table_without_geometry(owner_engine: Engine, extent_schema: str) -> None:
    _create_table(owner_engine, "CREATE TABLE extent.no_geom (code text)")

    assert read_table_extent(owner_engine, extent_schema, "no_geom") == TableExtent()
