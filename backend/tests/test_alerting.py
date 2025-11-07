"""Tests for alerting services."""
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models import (
    AlertComparator,
    AlertOccurrence,
    AlertPolicy,
    AlertSeverity,
    AlertStatus,
    Asset,
    Group,
    KPISnapshot,
)
from app.services import (
    AlertEvaluationService,
    AlertEventLogService,
    AlertNotificationService,
    AlertOccurrenceService,
    AlertPolicyService,
)


class TestAlertPolicyService:
    def test_create_policy(self, db: Session):
        """Test creating an alert policy."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            description="Test policy description",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            severity=AlertSeverity.HIGH,
            deduplication_window_minutes=30,
            email_recipients=["test@example.com"],
            webhook_url="https://example.com/webhook",
        )

        assert policy.id is not None
        assert policy.name == "Test Policy"
        assert policy.metric_name == "rolling"
        assert policy.comparator == AlertComparator.GREATER_THAN
        assert policy.threshold == 90.0
        assert policy.severity == AlertSeverity.HIGH
        assert policy.deduplication_window_minutes == 30
        assert json.loads(policy.email_recipients) == ["test@example.com"]
        assert policy.webhook_url == "https://example.com/webhook"

    def test_get_policy_by_id(self, db: Session):
        """Test getting a policy by ID."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        retrieved = AlertPolicyService.get_policy_by_id(db, policy.id)
        assert retrieved is not None
        assert retrieved.id == policy.id
        assert retrieved.name == "Test Policy"

    def test_get_policy_by_name(self, db: Session):
        """Test getting a policy by name."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        retrieved = AlertPolicyService.get_policy_by_name(db, "Test Policy")
        assert retrieved is not None
        assert retrieved.id == policy.id

    def test_list_policies(self, db: Session):
        """Test listing policies."""
        # Create active and inactive policies
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

        # Test active only (default)
        active_policies = AlertPolicyService.list_policies(db)
        assert len(active_policies) == 1
        assert active_policies[0].name == "Active Policy"

        # Test all policies
        all_policies = AlertPolicyService.list_policies(db, active_only=False)
        assert len(all_policies) == 2

    def test_update_policy(self, db: Session):
        """Test updating a policy."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        updated = AlertPolicyService.update_policy(
            db, policy.id, threshold=95.0, severity=AlertSeverity.CRITICAL
        )

        assert updated is not None
        assert updated.threshold == 95.0
        assert updated.severity == AlertSeverity.CRITICAL

    def test_delete_policy(self, db: Session):
        """Test deleting a policy."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        success = AlertPolicyService.delete_policy(db, policy.id)
        assert success is True

        retrieved = AlertPolicyService.get_policy_by_id(db, policy.id)
        assert retrieved is None


class TestAlertEvaluationService:
    def test_evaluate_threshold_greater_than(self):
        """Test greater than comparator."""
        assert AlertEvaluationService.evaluate_threshold(95.0, AlertComparator.GREATER_THAN, 90.0) is True
        assert AlertEvaluationService.evaluate_threshold(90.0, AlertComparator.GREATER_THAN, 90.0) is False
        assert AlertEvaluationService.evaluate_threshold(85.0, AlertComparator.GREATER_THAN, 90.0) is False

    def test_evaluate_threshold_less_than(self):
        """Test less than comparator."""
        assert AlertEvaluationService.evaluate_threshold(85.0, AlertComparator.LESS_THAN, 90.0) is True
        assert AlertEvaluationService.evaluate_threshold(90.0, AlertComparator.LESS_THAN, 90.0) is False
        assert AlertEvaluationService.evaluate_threshold(95.0, AlertComparator.LESS_THAN, 90.0) is False

    def test_evaluate_threshold_equal(self):
        """Test equal comparator."""
        assert AlertEvaluationService.evaluate_threshold(90.0, AlertComparator.EQUAL, 90.0) is True
        assert AlertEvaluationService.evaluate_threshold(85.0, AlertComparator.EQUAL, 90.0) is False

    def test_evaluate_policies_for_snapshot(self, db: Session):
        """Test evaluating policies for a KPI snapshot."""
        # Create asset and policy
        asset = AssetService.create_asset(db, "Test Asset")
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        # Create KPI snapshot that should trigger alert
        snapshot = KPISnapshot(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            kpi_type="rolling",
            value=95.0,
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(snapshot)
        db.commit()

        # Evaluate policies
        triggered_alerts = AlertEvaluationService.evaluate_policies_for_snapshot(db, snapshot)

        assert len(triggered_alerts) == 1
        assert triggered_alerts[0].policy_id == policy.id
        assert triggered_alerts[0].asset_id == asset.id
        assert triggered_alerts[0].current_value == 95.0
        assert triggered_alerts[0].threshold_value == 90.0


class TestAlertOccurrenceService:
    def test_create_occurrence(self, db: Session):
        """Test creating an alert occurrence."""
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
            message="Test alert message",
        )

        assert occurrence.id is not None
        assert occurrence.policy_id == policy.id
        assert occurrence.status == AlertStatus.ACTIVE
        assert occurrence.severity == AlertSeverity.HIGH
        assert occurrence.current_value == 95.0
        assert occurrence.threshold_value == 90.0

    def test_acknowledge_alert(self, db: Session):
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
            message="Test alert message",
        )

        user_id = str(uuid.uuid4())
        acknowledged = AlertOccurrenceService.acknowledge_alert(
            db, occurrence.id, user_id, "Acknowledged for investigation"
        )

        assert acknowledged is not None
        assert acknowledged.status == AlertStatus.ACKNOWLEDGED
        assert acknowledged.acknowledged_by == user_id
        assert acknowledged.acknowledged_at is not None

        # Check event log
        events = AlertEventLogService.get_event_logs(db, occurrence.id)
        assert len(events) == 1
        assert events[0].event_type == "ACKNOWLEDGED"
        assert user_id in events[0].message

    def test_resolve_alert(self, db: Session):
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
            message="Test alert message",
        )

        user_id = str(uuid.uuid4())
        resolved = AlertOccurrenceService.resolve_alert(
            db, occurrence.id, user_id, "Issue resolved"
        )

        assert resolved is not None
        assert resolved.status == AlertStatus.RESOLVED
        assert resolved.resolved_by == user_id
        assert resolved.resolved_at is not None

        # Check event log
        events = AlertEventLogService.get_event_logs(db, occurrence.id)
        assert len(events) == 1
        assert events[0].event_type == "RESOLVED"
        assert user_id in events[0].message

    def test_check_deduplication_window(self, db: Session):
        """Test deduplication window check."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            deduplication_window_minutes=60,
        )

        asset_id = str(uuid.uuid4())

        # Create an existing alert
        AlertOccurrenceService.create_occurrence(
            db=db,
            policy_id=policy.id,
            asset_id=asset_id,
            group_id=None,
            kpi_snapshot_id=str(uuid.uuid4()),
            severity=AlertSeverity.HIGH,
            current_value=95.0,
            threshold_value=90.0,
            message="Test alert message",
        )

        # Check deduplication window - should find the existing alert
        has_alert = AlertOccurrenceService.check_deduplication_window(
            db, policy.id, asset_id, None, 60
        )
        assert has_alert is True

        # Test with different asset - should not find alert
        different_asset_id = str(uuid.uuid4())
        has_alert = AlertOccurrenceService.check_deduplication_window(
            db, policy.id, different_asset_id, None, 60
        )
        assert has_alert is False


class TestAlertNotificationService:
    @patch('app.services.logger')
    def test_send_email_notification(self, mock_logger, db: Session):
        """Test email notification (mocked)."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            email_recipients=["test@example.com"],
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
            message="Test alert message",
        )

        # Test email notification (currently just logs)
        success = AlertNotificationService._send_email_notification(occurrence, policy)
        assert success is True
        mock_logger.info.assert_called()

    @patch('app.services.logger')
    def test_send_webhook_notification(self, mock_logger, db: Session):
        """Test webhook notification (mocked)."""
        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            webhook_url="https://example.com/webhook",
            webhook_secret="test-secret",
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
            message="Test alert message",
        )

        # Test webhook notification (currently just logs)
        success = AlertNotificationService._send_webhook_notification(occurrence, policy)
        assert success is True
        mock_logger.info.assert_called()


# Fixtures for testing
@pytest.fixture
def AssetService():
    from app.services import AssetService
    return AssetService