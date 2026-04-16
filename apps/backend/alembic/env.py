import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Literal, MutableMapping

from alembic import context
from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

# Make src importable when alembic is run from apps/backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import all DB-backed models so SQLModel.metadata is fully populated before
# Alembic inspects it. Imports are intentional side-effects — not unused.
from src.core.config import get_settings  # noqa: E402
from src.models.integrity_link import IntegrityLink  # noqa: E402
from src.models.integrity_link_rule import IntegrityLinkRule  # noqa: E402
from src.models.user import User  # noqa: E402

# Explicit reference so type checkers don't flag these as unused imports.
_MODELS = (IntegrityLink, IntegrityLinkRule, User)  # side-effect imports

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = SQLModel.metadata

IncludeNameType = Literal[
    "schema", "table", "column", "index", "unique_constraint", "foreign_key_constraint"
]
ParentNamesType = MutableMapping[
    Literal["schema_name", "table_name", "schema_qualified_table_name"], str | None
]


def get_url() -> str:
    return str(get_settings().POSTGRES_DATAFEEDER_URI)


def include_name(name: str | None, type_: IncludeNameType, _parent_names: ParentNamesType) -> bool:
    """Restrict Alembic to the datafeeder schema only.

    The public.user table is owned by geOrchestra and must not be managed here.
    """
    if type_ == "schema":
        return name == "datafeeder"
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="datafeeder",
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema="datafeeder",
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
