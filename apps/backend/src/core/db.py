from sqlmodel import create_engine

from src.core.config import get_settings

# Create database engine
engine = create_engine(str(get_settings().sqlalchemy_database_uri()))
