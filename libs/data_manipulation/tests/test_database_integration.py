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

from data_manipulation.database import list_tables_by_schema

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
