from sqlmodel import create_engine

from src.core.config import get_settings

# Create database engine
datafeeder_engine = create_engine(
    str(get_settings().POSTGRES_DATAFEEDER_URI), pool_pre_ping=True, pool_recycle=1800
)
data_engine = create_engine(
    str(get_settings().POSTGRES_DATA_URI), pool_pre_ping=True, pool_recycle=1800
)
