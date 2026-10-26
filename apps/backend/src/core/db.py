from sqlmodel import create_engine

from src.core.config import CopySourceDatabase, get_settings

# Create database engines
datafeeder_engine = create_engine(
    str(get_settings().POSTGRES_DATAFEEDER_URI), pool_pre_ping=True, pool_recycle=1800
)

data_engine = create_engine(
    str(get_settings().POSTGRES_DATA_URI), pool_pre_ping=True, pool_recycle=1800
)

# Only one copy source database is supported for now; take the first one if present.
# source_engine / source_db_key are None when SOURCE_DATABASES has no copy entry — callers must
# guard (staging.py returns 503 when source_engine is None).
source_db_key, _source_db = next(
    (
        (key, db)
        for key, db in get_settings().SOURCE_DATABASES.items()
        if isinstance(db, CopySourceDatabase)
    ),
    (None, None),
)
source_engine = (
    create_engine(str(_source_db.connection_string), pool_pre_ping=True, pool_recycle=1800)
    if _source_db
    else None
)
