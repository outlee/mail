from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


@pytest.fixture(scope="session")
def test_db():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_db):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_time():
    """Provide a consistent sample time for tests."""
    return datetime(2024, 1, 15, 10, 30, 0)


@pytest.fixture
def future_time():
    """Provide a future time for tests."""
    return datetime.utcnow() + timedelta(days=1)


@pytest.fixture
def past_time():
    """Provide a past time for tests."""
    return datetime.utcnow() - timedelta(days=30)


# Test data fixtures for common scenarios
@pytest.fixture
def zero_failures_data():
    """Test data scenario: asset with no failures."""
    return {
        "total_runtime": Decimal("720.0"),  # 30 days
        "failure_count": 0,
        "total_downtime": Decimal("0"),
        "expected_mtbf": None,
        "expected_failure_rate": Decimal("0"),
        "expected_mttr": None,
        "expected_availability": Decimal("1.0"),
    }


@pytest.fixture
def single_failure_data():
    """Test data scenario: asset with single failure."""
    return {
        "total_runtime": Decimal("720.0"),  # 30 days
        "failure_count": 1,
        "total_downtime": Decimal("4.0"),
        "expected_mtbf": Decimal("720.0"),
        "expected_failure_rate": Decimal("0.001389"),
        "expected_mttr": Decimal("4.0"),
        "expected_availability": Decimal("0.9944"),
    }


@pytest.fixture
def multiple_failures_data():
    """Test data scenario: asset with multiple failures."""
    return {
        "total_runtime": Decimal("720.0"),  # 30 days
        "failure_count": 3,
        "total_downtime": Decimal("6.0"),
        "expected_mtbf": Decimal("240.0"),
        "expected_failure_rate": Decimal("0.004167"),
        "expected_mttr": Decimal("2.0"),
        "expected_availability": Decimal("0.9917"),
    }


@pytest.fixture
def zero_runtime_data():
    """Test data scenario: asset with zero runtime."""
    return {
        "total_runtime": Decimal("0"),
        "failure_count": 0,
        "total_downtime": Decimal("0"),
        "expected_mtbf": None,
        "expected_failure_rate": Decimal("0"),
        "expected_mttr": None,
        "expected_availability": None,
    }
