from sqlmodel import create_engine

from src.core.config import get_settings

# Create database engines
datafeeder_engine = create_engine(
    str(get_settings().POSTGRES_DATAFEEDER_URI), pool_pre_ping=True, pool_recycle=1800
)

data_engine = create_engine(
    str(get_settings().POSTGRES_DATA_URI), pool_pre_ping=True, pool_recycle=1800
)

# Only one source database is supported for now; take the first entry if present.
# source_engine / source_db_key are None when SOURCE_DATABASES is empty — callers must guard
# (staging.py returns 503 when source_engine is None).
source_db_key, _source_db_value = next(iter(get_settings().SOURCE_DATABASES.items()), (None, None))
source_engine = (
    create_engine(str(_source_db_value), pool_pre_ping=True, pool_recycle=1800)
    if _source_db_value
    else None
)
