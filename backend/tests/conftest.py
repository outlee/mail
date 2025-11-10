import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from app.database import Base
from app.main import app
from app.models import Asset, Group, KPISnapshot, TaskRun, TaskRunStatus, User, UserRole
from app.security import hash_password

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/mtbf_test"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_user(db: Session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def maintainer_user(db: Session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email="maintainer@example.com",
        hashed_password=hash_password("password123"),
        full_name="Maintainer User",
        role=UserRole.MAINTAINER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_asset(db: Session) -> Asset:
    asset = Asset(
        id=str(uuid.uuid4()),
        name="Test Asset",
        description="Test asset description",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@pytest.fixture
def sample_group(db: Session) -> Group:
    group = Group(
        id=str(uuid.uuid4()),
        name="Test Group",
        description="Test group description",
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@pytest.fixture
def sample_kpi_snapshot(db: Session, sample_asset: Asset) -> KPISnapshot:
    now = datetime.utcnow()
    snapshot = KPISnapshot(
        id=str(uuid.uuid4()),
        asset_id=sample_asset.id,
        kpi_type="rolling",
        value=95.5,
        period_start=now,
        period_end=now + timedelta(days=1),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@pytest.fixture
def sample_task_run(db: Session) -> TaskRun:
    task_run = TaskRun(
        id=str(uuid.uuid4()),
        task_name="test_task",
        status=TaskRunStatus.PENDING,
        scope="test",
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)
    return task_run
