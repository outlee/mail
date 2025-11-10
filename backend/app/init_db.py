"""Initialize database tables."""
from app.database import Base, engine
from app.models import (
    Asset,
    CSVImportJob,
    FailureEvent,
    Group,
    KPISnapshot,
    RefreshToken,
    RuntimeCounter,
    TaskRun,
    User,
)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully!")


if __name__ == "__main__":
    init_db()
