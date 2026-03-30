from sqlmodel import create_engine

from src.core.config import get_settings

# Create database engines
datafeeder_engine = create_engine(
    str(get_settings().POSTGRES_DATAFEEDER_URI), pool_pre_ping=True, pool_recycle=1800
)

data_engine = create_engine(
    str(get_settings().POSTGRES_DATA_URI), pool_pre_ping=True, pool_recycle=1800
)

# Notes: only one source database supported for now, so we take the first entry if it exists
source_db_key, _source_db_value = next(iter(get_settings().SOURCE_DATABASES.items()), (None, None))
source_engine = (
    create_engine(str(_source_db_value), pool_pre_ping=True, pool_recycle=1800)
    if _source_db_value
    else None
)
