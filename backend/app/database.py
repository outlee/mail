from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.base import Base

settings = get_settings()

engine = create_engine(str(settings.database_url))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import all models to ensure they are registered with Base
from app.models import *  # noqa: F401,F403


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
