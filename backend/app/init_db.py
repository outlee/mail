"""Initialize database tables."""
from app.database import Base, engine
from app.models import (
    Asset,
    FailureEvent,
    Group,
    KPISnapshot,
    RefreshToken,
    TaskRun,
    User,
)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully!")


if __name__ == "__main__":
    init_db()
