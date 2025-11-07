from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Asset, AssetGroup, Base, Failure, RuntimeRecord
from app.schemas import Asset as AssetSchema, AssetGroup as AssetGroupSchema, Failure as FailureSchema, RuntimeRecord as RuntimeRecordSchema


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_db():
    """Create test database engine for API tests."""
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # Import all models to ensure they're registered with Base

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_db):
    """Create a test database session for API tests."""
    from sqlalchemy.orm import sessionmaker

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)

    # Override the dependency for testing
    from app.database import get_db
    from app.main import app

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal()  # Use the same session for the fixture

    app.dependency_overrides.clear()


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
def sample_data(db_session, sample_asset):
    """Create sample runtime and failure data."""
    base_time = datetime.utcnow() - timedelta(days=15)  # Within 30-day window

    # Add runtime data
    runtime = RuntimeRecord(
        asset_id=sample_asset.id,
        start_time=base_time,
        end_time=base_time + timedelta(hours=24),
        runtime_hours=Decimal("24.0"),
        is_active=False,
    )
    db_session.add(runtime)

    # Add failure data
    failure = Failure(
        asset_id=sample_asset.id,
        failure_time=base_time + timedelta(hours=12),
        recovery_time=base_time + timedelta(hours=14),
        downtime_hours=Decimal("2.0"),
        failure_code="F001",
        description="Test failure",
        is_resolved=True,
    )
    db_session.add(failure)

    db_session.commit()
    return {"runtime": runtime, "failure": failure}


class TestAPIEndpoints:
    """Test cases for API endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "environment" in data

    # Asset Management Tests
    def test_create_asset(self, client, sample_asset_group):
        """Test creating a new asset."""
        asset_data = {
            "name": "New Test Asset",
            "description": "New asset description",
            "asset_group_id": sample_asset_group.id,
            "is_active": True,
        }

        response = client.post("/api/v1/assets", json=asset_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "New Test Asset"
        assert data["description"] == "New asset description"
        assert data["asset_group_id"] == sample_asset_group.id
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_list_assets(self, client, sample_asset):
        """Test listing assets."""
        response = client.get("/api/v1/assets")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check that our sample asset is in the list
        asset_names = [asset["name"] for asset in data]
        assert "Test Asset" in asset_names

    def test_get_asset(self, client, sample_asset):
        """Test getting a specific asset."""
        response = client.get(f"/api/v1/assets/{sample_asset.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == sample_asset.id
        assert data["name"] == "Test Asset"
        assert data["description"] == "Test asset description"

    def test_get_asset_not_found(self, client):
        """Test getting a non-existent asset."""
        response = client.get("/api/v1/assets/999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_assets_with_filters(self, client, sample_asset, sample_asset_group):
        """Test listing assets with filters."""
        # Filter by asset group
        response = client.get(f"/api/v1/assets?asset_group_id={sample_asset_group.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["asset_group_id"] == sample_asset_group.id

        # Filter by active status
        response = client.get("/api/v1/assets?is_active=true")
        assert response.status_code == 200
        data = response.json()
        for asset in data:
            assert asset["is_active"] is True

    # Asset Group Management Tests
    def test_create_asset_group(self, client):
        """Test creating a new asset group."""
        group_data = {"name": "New Test Group", "description": "New asset group description"}

        response = client.post("/api/v1/asset-groups", json=group_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "New Test Group"
        assert data["description"] == "New asset group description"
        assert "id" in data
        assert "created_at" in data

    def test_list_asset_groups(self, client, sample_asset_group):
        """Test listing asset groups."""
        response = client.get("/api/v1/asset-groups")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        group_names = [group["name"] for group in data]
        assert "Test Group" in group_names

    def test_get_asset_group(self, client, sample_asset_group):
        """Test getting a specific asset group."""
        response = client.get(f"/api/v1/asset-groups/{sample_asset_group.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == sample_asset_group.id
        assert data["name"] == "Test Group"

    # Runtime Record Tests
    def test_create_runtime_record(self, client, sample_asset):
        """Test creating a runtime record."""
        runtime_data = {
            "asset_id": sample_asset.id,
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-02T00:00:00Z",
            "runtime_hours": "24.000",
            "is_active": False,
        }

        response = client.post("/api/v1/runtime-records", json=runtime_data)
        assert response.status_code == 200

        data = response.json()
        assert data["asset_id"] == sample_asset.id
        assert data["runtime_hours"] == "24.000"
        assert data["is_active"] is False

    def test_get_asset_runtime_records(self, client, sample_asset, sample_data):
        """Test getting runtime records for an asset."""
        response = client.get(f"/api/v1/assets/{sample_asset.id}/runtime-records")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    # Failure Management Tests
    def test_create_failure(self, client, sample_asset):
        """Test creating a failure record."""
        failure_data = {
            "asset_id": sample_asset.id,
            "failure_time": "2024-01-01T12:00:00Z",
            "recovery_time": "2024-01-01T14:00:00Z",
            "downtime_hours": "2.000",
            "failure_code": "F001",
            "description": "Test failure",
            "is_resolved": True,
        }

        response = client.post("/api/v1/failures", json=failure_data)
        assert response.status_code == 200

        data = response.json()
        assert data["asset_id"] == sample_asset.id
        assert data["failure_code"] == "F001"
        assert data["is_resolved"] is True

    def test_get_asset_failures(self, client, sample_asset, sample_data):
        """Test getting failure records for an asset."""
        response = client.get(f"/api/v1/assets/{sample_asset.id}/failures")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_update_failure(self, client, sample_asset, sample_data):
        """Test updating a failure record."""
        failure = sample_data["failure"]

        update_data = {"is_resolved": False, "description": "Updated failure description"}

        response = client.put(f"/api/v1/failures/{failure.id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["is_resolved"] is False
        assert data["description"] == "Updated failure description"

    def test_update_failure_not_found(self, client):
        """Test updating a non-existent failure."""
        update_data = {"is_resolved": False}

        response = client.put("/api/v1/failures/999999", json=update_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    # KPI Computation Tests
    def test_compute_kpis(self, client, sample_asset, sample_data):
        """Test KPI computation endpoint."""
        kpi_request = {"asset_id": sample_asset.id, "window_type": "rolling", "granularity": "30d"}

        response = client.post("/api/v1/kpis/compute", json=kpi_request)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        snapshot = data[0]
        assert snapshot["asset_id"] == sample_asset.id
        assert snapshot["window_type"] == "rolling"
        assert snapshot["granularity"] == "30d"
        assert snapshot["failure_count"] == 1
        assert snapshot["total_downtime_hours"] == "2.000"
        assert "mtbf" in snapshot
        assert "failure_rate" in snapshot
        assert "mttr" in snapshot
        assert "availability" in snapshot
        assert "computed_at" in snapshot

    def test_compute_kpis_invalid_request(self, client):
        """Test KPI computation with invalid request."""
        # Missing both asset_id and asset_group_id
        kpi_request = {"window_type": "rolling", "granularity": "30d"}

        response = client.post("/api/v1/kpis/compute", json=kpi_request)
        assert response.status_code == 422  # FastAPI returns 422 for validation errors

        # Invalid window type
        kpi_request = {"asset_id": 1, "window_type": "invalid", "granularity": "30d"}

        response = client.post("/api/v1/kpis/compute", json=kpi_request)
        assert response.status_code == 422  # FastAPI returns 422 for validation errors

    def test_get_kpis(self, client, sample_asset, sample_data):
        """Test getting KPI snapshots."""
        # First compute some KPIs
        kpi_request = {"asset_id": sample_asset.id, "window_type": "rolling", "granularity": "30d"}
        client.post("/api/v1/kpis/compute", json=kpi_request)

        # Then retrieve them
        response = client.get("/api/v1/kpis")
        assert response.status_code == 200

        data = response.json()
        assert "snapshots" in data
        assert "total" in data
        assert isinstance(data["snapshots"], list)
        assert data["total"] == len(data["snapshots"])

    def test_get_kpis_with_filters(self, client, sample_asset, sample_data):
        """Test getting KPI snapshots with filters."""
        # Compute KPIs with different parameters
        kpi_requests = [
            {"asset_id": sample_asset.id, "window_type": "rolling", "granularity": "30d"},
            {"asset_id": sample_asset.id, "window_type": "calendar", "granularity": "month"},
        ]

        for request in kpi_requests:
            client.post("/api/v1/kpis/compute", json=request)

        # Test filtering by asset_id
        response = client.get(f"/api/v1/kpis?asset_id={sample_asset.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

        # Test filtering by window_type
        response = client.get(f"/api/v1/kpis?asset_id={sample_asset.id}&window_type=rolling")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["snapshots"][0]["window_type"] == "rolling"

        # Test filtering by granularity
        response = client.get(f"/api/v1/kpis?asset_id={sample_asset.id}&granularity=30d")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["snapshots"][0]["granularity"] == "30d"

    def test_compute_kpis_asset_group(self, client, sample_asset, sample_asset_group, sample_data):
        """Test KPI computation for asset group."""
        kpi_request = {
            "asset_group_id": sample_asset_group.id,
            "window_type": "rolling",
            "granularity": "30d",
        }

        response = client.post("/api/v1/kpis/compute", json=kpi_request)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        snapshot = data[0]
        assert snapshot["asset_group_id"] == sample_asset_group.id
        assert snapshot["asset_id"] is None
        assert snapshot["failure_count"] == 1
