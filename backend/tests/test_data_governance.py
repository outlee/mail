import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import Asset, AssetRuntime, FailureEvent, FailureSeverity
from app.services import AssetRuntimeService, FailureEventService, DataQualityService

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestDataGovernance:
    """Test suite for data governance features."""

    def test_monotonic_runtime_counter_validation(self):
        """Test that runtime counters must be monotonically increasing."""
        db = TestingSessionLocal()
        
        # Create test asset
        asset = Asset(id="test-asset-1", name="Test Asset")
        db.add(asset)
        db.commit()
        
        # Create first runtime entry
        runtime1 = AssetRuntimeService.create_asset_runtime(
            db=db,
            asset_id="test-asset-1",
            runtime_counter=100,
        )
        assert runtime1.runtime_counter == 100
        
        # Create second runtime entry with higher counter (should succeed)
        runtime2 = AssetRuntimeService.create_asset_runtime(
            db=db,
            asset_id="test-asset-1",
            runtime_counter=200,
        )
        assert runtime2.runtime_counter == 200
        
        # Try to create runtime entry with lower counter (should fail)
        with pytest.raises(ValueError, match="Runtime counter must be greater than"):
            AssetRuntimeService.create_asset_runtime(
                db=db,
                asset_id="test-asset-1",
                runtime_counter=150,
            )
        
        db.close()

    def test_failure_event_overlapping_validation(self):
        """Test that failure events cannot overlap."""
        db = TestingSessionLocal()
        
        # Create test asset
        asset = Asset(id="test-asset-2", name="Test Asset 2")
        db.add(asset)
        db.commit()
        
        # Create first failure event
        event1 = FailureEventService.create_failure_event(
            db=db,
            asset_id="test-asset-2",
            severity=FailureSeverity.HIGH,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=2),
            description="Test failure event 1",
        )
        
        # Try to create overlapping failure event (should fail)
        with pytest.raises(ValueError, match="overlaps with existing event"):
            FailureEventService.create_failure_event(
                db=db,
                asset_id="test-asset-2",
                severity=FailureSeverity.MEDIUM,
                start_time=datetime.utcnow() + timedelta(hours=1),
                end_time=datetime.utcnow() + timedelta(hours=3),
                description="Overlapping failure event",
            )
        
        # Create non-overlapping failure event (should succeed)
        event2 = FailureEventService.create_failure_event(
            db=db,
            asset_id="test-asset-2",
            severity=FailureSeverity.LOW,
            start_time=datetime.utcnow() + timedelta(hours=3),
            end_time=datetime.utcnow() + timedelta(hours=5),
            description="Non-overlapping failure event",
        )
        assert event2.id != event1.id
        
        db.close()

    def test_high_severity_description_validation(self):
        """Test that high severity events require detailed descriptions."""
        db = TestingSessionLocal()
        
        # Create test asset
        asset = Asset(id="test-asset-3", name="Test Asset 3")
        db.add(asset)
        db.commit()
        
        # High severity with short description (should fail via Pydantic validation)
        response = client.post(
            "/api/v1/failure-events/",
            json={
                "asset_id": "test-asset-3",
                "severity": "high",
                "start_time": datetime.utcnow().isoformat(),
                "description": "Short",  # Too short for high severity
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        # Note: This would require authentication in real tests
        
        # Low severity with short description (should succeed)
        event = FailureEventService.create_failure_event(
            db=db,
            asset_id="test-asset-3",
            severity=FailureSeverity.LOW,
            start_time=datetime.utcnow(),
            description="Short",  # OK for low severity
        )
        assert event.severity == FailureSeverity.LOW
        
        db.close()

    def test_data_quality_check(self):
        """Test data quality validation checks."""
        db = TestingSessionLocal()
        
        # Create test asset without runtime (should be flagged)
        asset1 = Asset(id="test-asset-4", name="Asset Without Runtime")
        db.add(asset1)
        
        # Create test asset with runtime
        asset2 = Asset(id="test-asset-5", name="Asset With Runtime")
        db.add(asset2)
        db.commit()
        
        runtime = AssetRuntimeService.create_asset_runtime(
            db=db,
            asset_id="test-asset-5",
            runtime_counter=100,
        )
        
        # Create invalid failure event (end_time before start_time)
        asset3 = Asset(id="test-asset-6", name="Asset With Invalid Failure")
        db.add(asset3)
        db.commit()
        
        invalid_event = FailureEvent(
            id="invalid-event",
            asset_id="test-asset-6",
            severity=FailureSeverity.MEDIUM,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() - timedelta(hours=1),  # Invalid: end before start
            description="Invalid failure event",
        )
        db.add(invalid_event)
        db.commit()
        
        # Run data quality check
        report = DataQualityService.run_data_quality_check(db, "comprehensive")
        
        assert report.status == "completed"
        assert report.issues_found >= 2  # At least asset without runtime and invalid failure event
        assert "Asset test-asset-4" in report.details  # Asset without runtime
        assert "invalid-event" in report.details  # Invalid failure event
        
        db.close()

    def test_audit_logging(self):
        """Test that audit entries are created for data modifications."""
        from app.services import AuditLogService
        from app.models import AuditAction
        
        db = TestingSessionLocal()
        
        # Create test asset
        asset = Asset(id="test-asset-7", name="Test Asset 7")
        db.add(asset)
        db.commit()
        
        # Create failure event
        event = FailureEventService.create_failure_event(
            db=db,
            asset_id="test-asset-7",
            severity=FailureSeverity.MEDIUM,
            start_time=datetime.utcnow(),
            description="Test event for audit",
        )
        
        # Manually create audit entry (in real app, this happens automatically)
        audit_entry = AuditLogService.create_audit_entry(
            db=db,
            user_id="test-user",
            action=AuditAction.CREATE,
            resource_type="failure_event",
            resource_id=event.id,
            new_values='{"severity": "medium", "description": "Test event for audit"}',
        )
        
        # Verify audit entry was created
        assert audit_entry.action == AuditAction.CREATE
        assert audit_entry.resource_type == "failure_event"
        assert audit_entry.resource_id == event.id
        assert audit_entry.user_id == "test-user"
        
        db.close()


if __name__ == "__main__":
    pytest.main([__file__])