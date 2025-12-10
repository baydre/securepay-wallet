from databases import Database
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Base class for models (defined first to avoid circular imports)
Base = declarative_base()

# These will be initialized by the app
database = None
engine = None
SessionLocal = None


def init_database():
    """Initialize database connections - called by main app"""
    global database, engine, SessionLocal
    
    from config import get_settings
    settings = get_settings()
    
    database = Database(settings.database_url)
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return database, engine, SessionLocal


async def get_database():
    """Dependency for getting database connection"""
    return database
