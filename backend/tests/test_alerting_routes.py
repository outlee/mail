"""Tests for alerting API routes."""
import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import UserRole, AlertSeverity, AlertComparator
from app.services import AlertPolicyService, AlertOccurrenceService


client = TestClient(app)


class TestAlertPolicyRoutes:
    def test_create_policy_success(self, db: Session, maintainer_token: str):
        """Test successful policy creation."""
        policy_data = {
            "name": "Test Policy",
            "description": "Test policy description",
            "metric_name": "rolling",
            "comparator": "gt",
            "threshold": 90.0,
            "severity": "high",
            "deduplication_window_minutes": 30,
            "email_recipients": ["test@example.com"],
            "webhook_url": "https://example.com/webhook",
            "is_active": True,
        }

        response = client.post(
            "/api/v1/alerts/policies",
            json=policy_data,
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Policy"
        assert data["metric_name"] == "rolling"
        assert data["comparator"] == "gt"
        assert data["threshold"] == 90.0
        assert data["severity"] == "high"

    def test_create_policy_duplicate_name(self, db: Session, maintainer_token: str):
        """Test policy creation with duplicate name."""
        # Create first policy
        AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        policy_data = {
            "name": "Test Policy",  # Same name
            "metric_name": "rolling",
            "comparator": "gt",
            "threshold": 85.0,
        }

        response = client.post(
            "/api/v1/alerts/policies",
            json=policy_data,
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_policy_unauthorized(self, db: Session):
        """Test policy creation without authentication."""
        policy_data = {
            "name": "Test Policy",
            "metric_name": "rolling",
            "comparator": "gt",
            "threshold": 90.0,
        }

        response = client.post("/api/v1/alerts/policies", json=policy_data)
        assert response.status_code == 401

    def test_create_policy_forbidden(self, db: Session, user_token: str):
        """Test policy creation with insufficient permissions."""
        policy_data = {
            "name": "Test Policy",
            "metric_name": "rolling",
            "comparator": "gt",
            "threshold": 90.0,
        }

        response = client.post(
            "/api/v1/alerts/policies",
            json=policy_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == 403

    def test_list_policies(self, db: Session, maintainer_token: str):
        """Test listing policies."""
        # Create test policies
        AlertPolicyService.create_policy(
            db=db,
            name="Active Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            is_active=True,
        )
        AlertPolicyService.create_policy(
            db=db,
            name="Inactive Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=80.0,
            is_active=False,
        )

        response = client.get(
            "/api/v1/alerts/policies",
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only active policies by default
        assert data[0]["name"] == "Active Policy"

    def test_list_all_policies(self, db: Session, maintainer_token: str):
        """Test listing all policies including inactive."""
        # Create test policies
        AlertPolicyService.create_policy(
            db=db,
            name="Active Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            is_active=True,
        )
        AlertPolicyService.create_policy(
            db=db,
            name="Inactive Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=80.0,
            is_active=False,
        )

        response = client.get(
            "/api/v1/alerts/policies?active_only=false",
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Both policies

    def test_get_policy_by_id(self, db: Session, maintainer_token: str):
        """Test getting a policy by ID."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        response = client.get(
            f"/api/v1/alerts/policies/{policy.id}",
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == policy.id
        assert data["name"] == "Test Policy"

    def test_get_policy_not_found(self, db: Session, maintainer_token: str):
        """Test getting a non-existent policy."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/alerts/policies/{fake_id}",
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 404

    def test_update_policy(self, db: Session, maintainer_token: str):
        """Test updating a policy."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        update_data = {
            "threshold": 95.0,
            "severity": "critical",
        }

        response = client.put(
            f"/api/v1/alerts/policies/{policy.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == 95.0
        assert data["severity"] == "critical"

    def test_update_policy_duplicate_name(self, db: Session, maintainer_token: str):
        """Test updating policy with duplicate name."""
        policy1 = AlertPolicyService.create_policy(
            db=db,
            name="Policy 1",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )
        policy2 = AlertPolicyService.create_policy(
            db=db,
            name="Policy 2",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=80.0,
        )

        update_data = {"name": "Policy 1"}  # Try to use policy1's name for policy2

        response = client.put(
            f"/api/v1/alerts/policies/{policy2.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 409

    def test_delete_policy(self, db: Session, maintainer_token: str):
        """Test deleting a policy."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        response = client.delete(
            f"/api/v1/alerts/policies/{policy.id}",
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 204

        # Verify policy is deleted
        retrieved = AlertPolicyService.get_policy_by_id(db, policy.id)
        assert retrieved is None

    def test_delete_policy_forbidden(self, db: Session, operator_token: str):
        """Test deleting policy with insufficient permissions."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        response = client.delete(
            f"/api/v1/alerts/policies/{policy.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 403


class TestAlertEventRoutes:
    def test_list_alert_events(self, db: Session, maintainer_token: str):
        """Test listing alert events."""
        # Create a test alert occurrence
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )
        
        occurrence = AlertOccurrenceService.create_occurrence(
            db=db,
            policy_id=policy.id,
            asset_id=str(uuid.uuid4()),
            group_id=None,
            kpi_snapshot_id=str(uuid.uuid4()),
            severity=AlertSeverity.HIGH,
            current_value=95.0,
            threshold_value=90.0,
            message="Test alert",
        )

        response = client.get(
            "/api/v1/alerts/events",
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["id"] == occurrence.id

    def test_list_alert_events_with_filters(self, db: Session, maintainer_token: str):
        """Test listing alert events with filters."""
        # Create test alerts with different severities
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )
        
        AlertOccurrenceService.create_occurrence(
            db=db,
            policy_id=policy.id,
            asset_id=str(uuid.uuid4()),
            group_id=None,
            kpi_snapshot_id=str(uuid.uuid4()),
            severity=AlertSeverity.HIGH,
            current_value=95.0,
            threshold_value=90.0,
            message="High severity alert",
        )
        
        AlertOccurrenceService.create_occurrence(
            db=db,
            policy_id=policy.id,
            asset_id=str(uuid.uuid4()),
            group_id=None,
            kpi_snapshot_id=str(uuid.uuid4()),
            severity=AlertSeverity.LOW,
            current_value=85.0,
            threshold_value=80.0,
            message="Low severity alert",
        )

        # Filter by severity
        response = client.get(
            "/api/v1/alerts/events?severity=high",
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["alerts"][0]["severity"] == "high"

    def test_acknowledge_alert(self, db: Session, maintainer_token: str):
        """Test acknowledging an alert."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )
        
        occurrence = AlertOccurrenceService.create_occurrence(
            db=db,
            policy_id=policy.id,
            asset_id=str(uuid.uuid4()),
            group_id=None,
            kpi_snapshot_id=str(uuid.uuid4()),
            severity=AlertSeverity.HIGH,
            current_value=95.0,
            threshold_value=90.0,
            message="Test alert",
        )

        user_id = str(uuid.uuid4())
        ack_data = {
            "user_id": user_id,
            "message": "Acknowledged for investigation",
        }

        response = client.post(
            f"/api/v1/alerts/events/{occurrence.id}/acknowledge",
            json=ack_data,
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"
        assert data["acknowledged_by"] == user_id
        assert data["acknowledged_at"] is not None

    def test_resolve_alert(self, db: Session, maintainer_token: str):
        """Test resolving an alert."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )
        
        occurrence = AlertOccurrenceService.create_occurrence(
            db=db,
            policy_id=policy.id,
            asset_id=str(uuid.uuid4()),
            group_id=None,
            kpi_snapshot_id=str(uuid.uuid4()),
            severity=AlertSeverity.HIGH,
            current_value=95.0,
            threshold_value=90.0,
            message="Test alert",
        )

        user_id = str(uuid.uuid4())
        resolve_data = {
            "user_id": user_id,
            "message": "Issue resolved",
        }

        response = client.post(
            f"/api/v1/alerts/events/{occurrence.id}/resolve",
            json=resolve_data,
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolved_by"] == user_id
        assert data["resolved_at"] is not None

    def test_acknowledge_nonexistent_alert(self, db: Session, maintainer_token: str):
        """Test acknowledging a non-existent alert."""
        fake_id = str(uuid.uuid4())
        ack_data = {
            "user_id": str(uuid.uuid4()),
            "message": "Test acknowledgment",
        }

        response = client.post(
            f"/api/v1/alerts/events/{fake_id}/acknowledge",
            json=ack_data,
            headers={"Authorization": f"Bearer {maintainer_token}"}
        )

        assert response.status_code == 404