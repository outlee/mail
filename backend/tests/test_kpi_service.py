from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.kpi_service import Granularity, KPIService, WindowType
from app.models import Asset, AssetGroup, Base, Failure, RuntimeRecord


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def kpi_service(db_session):
    """Create KPI service instance."""
    return KPIService(db_session)


@pytest.fixture
def sample_asset_group(db_session):
    """Create a sample asset group."""
    group = AssetGroup(name="Test Group", description="Test asset group")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)
    return group


@pytest.fixture
def sample_asset(db_session, sample_asset_group):
    """Create a sample asset."""
    asset = Asset(
        name="Test Asset",
        description="Test asset description",
        asset_group_id=sample_asset_group.id,
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def sample_runtime_data(db_session, sample_asset):
    """Create sample runtime records."""
    base_time = datetime.utcnow() - timedelta(days=15)  # Within 30-day window

    runtime_records = [
        RuntimeRecord(
            asset_id=sample_asset.id,
            start_time=base_time,
            end_time=base_time + timedelta(hours=24),
            runtime_hours=Decimal("24.0"),
            is_active=False,
        ),
        RuntimeRecord(
            asset_id=sample_asset.id,
            start_time=base_time + timedelta(days=1),
            end_time=base_time + timedelta(days=1, hours=24),
            runtime_hours=Decimal("24.0"),
            is_active=False,
        ),
        RuntimeRecord(
            asset_id=sample_asset.id,
            start_time=base_time + timedelta(days=2),
            end_time=base_time + timedelta(days=2, hours=24),
            runtime_hours=Decimal("24.0"),
            is_active=False,
        ),
    ]

    for record in runtime_records:
        db_session.add(record)

    db_session.commit()
    return runtime_records


@pytest.fixture
def sample_failure_data(db_session, sample_asset):
    """Create sample failure records."""
    base_time = datetime.utcnow() - timedelta(days=15)  # Within 30-day window

    failures = [
        Failure(
            asset_id=sample_asset.id,
            failure_time=base_time + timedelta(hours=12),
            recovery_time=base_time + timedelta(hours=14),
            downtime_hours=Decimal("2.0"),
            failure_code="F001",
            description="Test failure 1",
            is_resolved=True,
        ),
        Failure(
            asset_id=sample_asset.id,
            failure_time=base_time + timedelta(days=5, hours=12),
            recovery_time=base_time + timedelta(days=5, hours=15),
            downtime_hours=Decimal("3.0"),
            failure_code="F002",
            description="Test failure 2",
            is_resolved=True,
        ),
        Failure(
            asset_id=sample_asset.id,
            failure_time=base_time + timedelta(days=10, hours=12),
            recovery_time=base_time + timedelta(days=10, hours=13),
            downtime_hours=Decimal("1.0"),
            failure_code="F003",
            description="Test failure 3",
            is_resolved=True,
        ),
    ]

    for failure in failures:
        db_session.add(failure)

    db_session.commit()
    return failures


class TestKPIService:
    """Test cases for KPI service."""

    def test_compute_kpis_rolling_30d_with_failures(
        self, kpi_service, sample_asset, sample_runtime_data, sample_failure_data
    ):
        """Test KPI computation for 30-day rolling window with failures."""
        evaluation_time = datetime.utcnow()

        snapshots = kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.ROLLING,
            granularity=Granularity.DAYS_30,
            evaluation_time=evaluation_time,
        )

        assert len(snapshots) == 1
        snapshot = snapshots[0]

        # Verify window bounds
        expected_start = evaluation_time - timedelta(days=30)
        assert snapshot.window_start == expected_start
        assert snapshot.window_end == evaluation_time
        assert snapshot.window_type == "rolling"
        assert snapshot.granularity == "30d"
        assert snapshot.asset_id == sample_asset.id

        # Verify computed metrics (with failures)
        assert snapshot.failure_count == 3
        assert snapshot.total_runtime_hours is not None
        assert snapshot.total_downtime_hours == Decimal("6.0")  # 2+3+1 hours
        assert snapshot.mtbf is not None
        assert snapshot.mttr == Decimal("2.0")  # 6.0 / 3 failures
        assert snapshot.failure_rate is not None
        assert snapshot.availability is not None
        assert snapshot.availability < Decimal("1.0")  # Should be less than 100% due to downtime

        # Verify relationships
        assert snapshot.asset.name == "Test Asset"

    def test_compute_kpis_no_failures(self, kpi_service, sample_asset, sample_runtime_data):
        """Test KPI computation when there are no failures."""
        evaluation_time = datetime.utcnow()

        snapshots = kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.ROLLING,
            granularity=Granularity.DAYS_30,
            evaluation_time=evaluation_time,
        )

        assert len(snapshots) == 1
        snapshot = snapshots[0]

        # Verify metrics with no failures
        assert snapshot.failure_count == 0
        assert snapshot.mtbf is None  # Infinity when no failures
        assert snapshot.failure_rate == Decimal("0")
        assert snapshot.mttr is None
        # With runtime but no failures, availability should be 1.0
        assert snapshot.availability == Decimal("1.0")  # 100% when no downtime

    def test_compute_kpis_calendar_month(
        self, kpi_service, sample_asset, sample_runtime_data, sample_failure_data
    ):
        """Test KPI computation for calendar month window."""
        evaluation_time = datetime.utcnow()

        snapshots = kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.CALENDAR,
            granularity=Granularity.MONTH,
            evaluation_time=evaluation_time,
        )

        assert len(snapshots) == 1
        snapshot = snapshots[0]

        # Verify calendar month alignment
        expected_start = evaluation_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        assert snapshot.window_start == expected_start
        assert snapshot.window_type == "calendar"
        assert snapshot.granularity == "month"

    def test_compute_kpis_asset_group(
        self,
        kpi_service,
        sample_asset_group,
        sample_asset,
        sample_runtime_data,
        sample_failure_data,
    ):
        """Test KPI computation for asset group."""
        evaluation_time = datetime.utcnow()

        snapshots = kpi_service.compute_and_store_kpis(
            asset_group_id=sample_asset_group.id,
            window_type=WindowType.ROLLING,
            granularity=Granularity.DAYS_30,
            evaluation_time=evaluation_time,
        )

        assert len(snapshots) == 1
        snapshot = snapshots[0]

        # Verify group-level computation
        assert snapshot.asset_group_id == sample_asset_group.id
        assert snapshot.asset_id is None
        assert snapshot.failure_count == 3
        assert snapshot.asset_group.name == "Test Group"

    def test_get_latest_kpis_with_filters(
        self, kpi_service, sample_asset, sample_runtime_data, sample_failure_data
    ):
        """Test retrieving latest KPIs with filters."""
        # Create some snapshots first
        kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.ROLLING,
            granularity=Granularity.DAYS_30,
        )

        kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.CALENDAR,
            granularity=Granularity.MONTH,
        )

        # Test filtering by asset_id
        snapshots = kpi_service.get_latest_kpis(asset_id=sample_asset.id)
        assert len(snapshots) == 2

        # Test filtering by window_type
        snapshots = kpi_service.get_latest_kpis(
            asset_id=sample_asset.id, window_type=WindowType.ROLLING
        )
        assert len(snapshots) == 1
        assert snapshots[0].window_type == "rolling"

        # Test filtering by granularity
        snapshots = kpi_service.get_latest_kpis(
            asset_id=sample_asset.id, granularity=Granularity.DAYS_30
        )
        assert len(snapshots) == 1
        assert snapshots[0].granularity == "30d"

    def test_window_bounds_rolling(self, kpi_service):
        """Test rolling window bounds calculation."""
        evaluation_time = datetime(2024, 1, 15, 10, 30, 0)

        # Test 7-day rolling
        start, end = kpi_service._get_window_bounds(
            WindowType.ROLLING, Granularity.DAYS_7, evaluation_time
        )
        assert end == evaluation_time
        assert start == evaluation_time - timedelta(days=7)

        # Test 30-day rolling
        start, end = kpi_service._get_window_bounds(
            WindowType.ROLLING, Granularity.DAYS_30, evaluation_time
        )
        assert end == evaluation_time
        assert start == evaluation_time - timedelta(days=30)

        # Test 90-day rolling
        start, end = kpi_service._get_window_bounds(
            WindowType.ROLLING, Granularity.DAYS_90, evaluation_time
        )
        assert end == evaluation_time
        assert start == evaluation_time - timedelta(days=90)

    def test_window_bounds_calendar(self, kpi_service):
        """Test calendar window bounds calculation."""
        # Test day window
        evaluation_time = datetime(2024, 1, 15, 10, 30, 0)
        start, end = kpi_service._get_window_bounds(
            WindowType.CALENDAR, Granularity.DAY, evaluation_time
        )
        assert start == datetime(2024, 1, 15, 0, 0, 0)
        assert end == datetime(2024, 1, 16, 0, 0, 0)

        # Test week window (Monday start)
        evaluation_time = datetime(2024, 1, 15, 10, 30, 0)  # This is a Monday
        start, end = kpi_service._get_window_bounds(
            WindowType.CALENDAR, Granularity.WEEK, evaluation_time
        )
        assert start == datetime(2024, 1, 15, 0, 0, 0)
        assert end == datetime(2024, 1, 22, 0, 0, 0)

        # Test month window
        evaluation_time = datetime(2024, 1, 15, 10, 30, 0)
        start, end = kpi_service._get_window_bounds(
            WindowType.CALENDAR, Granularity.MONTH, evaluation_time
        )
        assert start == datetime(2024, 1, 1, 0, 0, 0)
        assert end == datetime(2024, 2, 1, 0, 0, 0)

    def test_idempotent_snapshot_creation(
        self, kpi_service, sample_asset, sample_runtime_data, sample_failure_data
    ):
        """Test that snapshot creation is idempotent."""
        evaluation_time = datetime.utcnow()

        # Create first snapshot
        snapshots1 = kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.ROLLING,
            granularity=Granularity.DAYS_30,
            evaluation_time=evaluation_time,
        )

        # Add a small delay to ensure different timestamps
        import time

        time.sleep(0.001)

        # Create second snapshot with same parameters
        snapshots2 = kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.ROLLING,
            granularity=Granularity.DAYS_30,
            evaluation_time=evaluation_time,
        )

        assert len(snapshots1) == 1
        assert len(snapshots2) == 1
        assert snapshots1[0].id == snapshots2[0].id  # Should be the same record
        assert snapshots2[0].computed_at >= snapshots1[0].computed_at  # Should be updated or same

    def test_edge_case_zero_runtime(self, kpi_service, sample_asset):
        """Test KPI computation when runtime is zero."""
        evaluation_time = datetime.utcnow()

        snapshots = kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.ROLLING,
            granularity=Granularity.DAYS_30,
            evaluation_time=evaluation_time,
        )

        assert len(snapshots) == 1
        snapshot = snapshots[0]

        # With zero runtime, availability should be None
        assert snapshot.total_runtime_hours is None or snapshot.total_runtime_hours == 0
        assert snapshot.availability is None
        assert snapshot.failure_rate == Decimal("0")

    def test_precision_rounding(
        self, kpi_service, sample_asset, sample_runtime_data, sample_failure_data
    ):
        """Test that metrics are properly rounded to specified precision."""
        evaluation_time = datetime.utcnow()

        snapshots = kpi_service.compute_and_store_kpis(
            asset_id=sample_asset.id,
            window_type=WindowType.ROLLING,
            granularity=Granularity.DAYS_30,
            evaluation_time=evaluation_time,
        )

        assert len(snapshots) == 1
        snapshot = snapshots[0]

        # Check that decimal places are preserved correctly
        if snapshot.mtbf is not None:
            assert len(str(snapshot.mtbf).split(".")[-1]) <= 3  # 3 decimal places
        if snapshot.failure_rate is not None:
            assert len(str(snapshot.failure_rate).split(".")[-1]) <= 6  # 6 decimal places
        if snapshot.mttr is not None:
            assert len(str(snapshot.mttr).split(".")[-1]) <= 3  # 3 decimal places
        if snapshot.availability is not None:
            assert len(str(snapshot.availability).split(".")[-1]) <= 4  # 4 decimal places
