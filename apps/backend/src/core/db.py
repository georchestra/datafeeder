from functools import lru_cache

from sqlalchemy import Engine
from sqlmodel import create_engine

from src.core.config import CopySourceDatabase, get_settings

# Create database engines
datafeeder_engine = create_engine(
    str(get_settings().POSTGRES_DATAFEEDER_URI), pool_pre_ping=True, pool_recycle=1800
)

data_engine = create_engine(
    str(get_settings().POSTGRES_DATA_URI), pool_pre_ping=True, pool_recycle=1800
)


@lru_cache
def get_source_engine(key: str) -> Engine | None:
    """Engine of any SOURCE_DATABASES entry (copy or direct access), None for an unknown key."""
    db = get_settings().SOURCE_DATABASES.get(key)
    if db is None:
        return None
    return create_engine(
        str(db.connection_string),
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"connect_timeout": 5},
    )


def get_copy_source_database(key: str | None) -> CopySourceDatabase | None:
    """Copy entry of SOURCE_DATABASES, None for an unknown key or a direct access entry."""
    db = get_settings().SOURCE_DATABASES.get(key) if key else None
    return db if isinstance(db, CopySourceDatabase) else None
