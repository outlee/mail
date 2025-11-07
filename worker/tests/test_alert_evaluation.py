"""Tests for alert evaluation worker task."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from celery import current_app as celery_app
from sqlalchemy.orm import Session

from worker.tasks import evaluate_alerts_task

from app.models import (
    AlertComparator,
    AlertOccurrence,
    AlertPolicy,
    AlertSeverity,
    AlertStatus,
    Asset,
    KPISnapshot,
)
from app.services import AlertPolicyService, AlertOccurrenceService


class TestAlertEvaluationTask:
    def test_evaluate_alerts_task_success(self, db: Session):
        """Test successful alert evaluation task."""
        # Create asset and policy
        asset = Asset(
            id=str(uuid.uuid4()),
            name="Test Asset",
        )
        db.add(asset)
        db.commit()

        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            severity=AlertSeverity.HIGH,
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

        # Run the task
        result = evaluate_alerts_task.apply(args=[None, snapshot.id]).result

        assert result["status"] == "success"
        assert result["items_processed"] == 1
        assert result["snapshot_id"] == snapshot.id

        # Check that alert was created
        occurrences, _ = AlertOccurrenceService.list_occurrences(db)
        assert len(occurrences) == 1
        assert occurrences[0].policy_id == policy.id
        assert occurrences[0].asset_id == asset.id
        assert occurrences[0].current_value == 95.0
        assert occurrences[0].threshold_value == 90.0
        assert occurrences[0].status == AlertStatus.ACTIVE

    def test_evaluate_alerts_task_no_trigger(self, db: Session):
        """Test alert evaluation task with no threshold crossing."""
        # Create asset and policy
        asset = Asset(
            id=str(uuid.uuid4()),
            name="Test Asset",
        )
        db.add(asset)
        db.commit()

        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            severity=AlertSeverity.HIGH,
        )

        # Create KPI snapshot that should NOT trigger alert
        snapshot = KPISnapshot(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            kpi_type="rolling",
            value=85.0,  # Below threshold
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(snapshot)
        db.commit()

        # Run the task
        result = evaluate_alerts_task.apply(args=[None, snapshot.id]).result

        assert result["status"] == "success"
        assert result["items_processed"] == 0

        # Check that no alert was created
        occurrences, _ = AlertOccurrenceService.list_occurrences(db)
        assert len(occurrences) == 0

    def test_evaluate_alerts_task_with_deduplication(self, db: Session):
        """Test alert evaluation with deduplication window."""
        # Create asset and policy with short deduplication window
        asset = Asset(
            id=str(uuid.uuid4()),
            name="Test Asset",
        )
        db.add(asset)
        db.commit()

        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            deduplication_window_minutes=60,  # 1 hour
        )

        # Create existing alert
        existing_occurrence = AlertOccurrenceService.create_occurrence(
            db=db,
            policy_id=policy.id,
            asset_id=asset.id,
            group_id=None,
            kpi_snapshot_id=str(uuid.uuid4()),
            severity=AlertSeverity.HIGH,
            current_value=95.0,
            threshold_value=90.0,
            message="Existing alert",
        )

        # Create new KPI snapshot that would normally trigger alert
        snapshot = KPISnapshot(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            kpi_type="rolling",
            value=96.0,  # Above threshold
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(snapshot)
        db.commit()

        # Run the task
        result = evaluate_alerts_task.apply(args=[None, snapshot.id]).result

        assert result["status"] == "success"
        assert result["items_processed"] == 0  # Should be 0 due to deduplication

        # Check that no new alert was created
        occurrences, _ = AlertOccurrenceService.list_occurrences(db)
        assert len(occurrences) == 1  # Only the existing one
        assert occurrences[0].id == existing_occurrence.id

    def test_evaluate_alerts_task_snapshot_not_found(self, db: Session):
        """Test alert evaluation with non-existent snapshot."""
        fake_snapshot_id = str(uuid.uuid4())

        # Run the task - should fail
        with pytest.raises(Exception):
            evaluate_alerts_task.apply(args=[None, fake_snapshot_id]).get()

    def test_evaluate_alerts_task_with_task_run(self, db: Session):
        """Test alert evaluation task with task run tracking."""
        from app.services import TaskRunService

        # Create task run
        task_run = TaskRunService.create_task_run(
            db=db,
            task_name="evaluate_alerts_task",
            scope="snapshot",
        )

        # Create asset and policy
        asset = Asset(
            id=str(uuid.uuid4()),
            name="Test Asset",
        )
        db.add(asset)
        db.commit()

        policy = AlertPolicyService.create_policy(
            db=db,
            name="Test Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
        )

        # Create KPI snapshot
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

        # Run the task with task run tracking
        result = evaluate_alerts_task.apply(args=[task_run.id, snapshot.id]).result

        assert result["status"] == "success"

        # Check task run was updated
        updated_task_run = TaskRunService.get_task_run(db, task_run.id)
        assert updated_task_run.status.value == "success"
        assert updated_task_run.items_processed == 1
        assert updated_task_run.completed_at is not None

    def test_evaluate_alerts_task_multiple_policies(self, db: Session):
        """Test alert evaluation with multiple matching policies."""
        # Create asset
        asset = Asset(
            id=str(uuid.uuid4()),
            name="Test Asset",
        )
        db.add(asset)
        db.commit()

        # Create multiple policies for the same metric
        policy1 = AlertPolicyService.create_policy(
            db=db,
            name="High Threshold Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=90.0,
            severity=AlertSeverity.HIGH,
        )

        policy2 = AlertPolicyService.create_policy(
            db=db,
            name="Critical Threshold Policy",
            metric_name="rolling",
            comparator=AlertComparator.GREATER_THAN,
            threshold=95.0,
            severity=AlertSeverity.CRITICAL,
        )

        # Create KPI snapshot that triggers both policies
        snapshot = KPISnapshot(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            kpi_type="rolling",
            value=97.0,  # Above both thresholds
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(snapshot)
        db.commit()

        # Run the task
        result = evaluate_alerts_task.apply(args=[None, snapshot.id]).result

        assert result["status"] == "success"
        assert result["items_processed"] == 2  # Should trigger 2 alerts

        # Check that both alerts were created
        occurrences, _ = AlertOccurrenceService.list_occurrences(db)
        assert len(occurrences) == 2
        
        policy_ids = [occ.policy_id for occ in occurrences]
        assert policy1.id in policy_ids
        assert policy2.id in policy_ids

    @patch('worker.tasks.logger')
    def test_evaluate_alerts_task_with_error(self, mock_logger, db: Session):
        """Test alert evaluation task error handling."""
        # Use invalid snapshot ID to trigger error
        fake_snapshot_id = str(uuid.uuid4())

        # Run the task - should retry
        task = evaluate_alerts_task.apply(args=[None, fake_snapshot_id])
        
        # Task should fail and be queued for retry
        assert task.status == 'FAILURE'
        mock_logger.error.assert_called()

    def test_evaluate_alerts_task_group_kpi(self, db: Session):
        """Test alert evaluation for group KPI."""
        # Create group and policy
        group = Asset(  # Using Asset as placeholder since Group model structure might differ
            id=str(uuid.uuid4()),
            name="Test Group",
        )
        db.add(group)
        db.commit()

        policy = AlertPolicyService.create_policy(
            db=db,
            name="Group Policy",
            metric_name="calendar",
            comparator=AlertComparator.LESS_THAN,
            threshold=85.0,
            severity=AlertSeverity.MEDIUM,
        )

        # Create group KPI snapshot that should trigger alert
        snapshot = KPISnapshot(
            id=str(uuid.uuid4()),
            group_id=group.id,  # Group KPI
            kpi_type="calendar",
            value=80.0,  # Below threshold for LESS_THAN
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(days=1),
        )
        db.add(snapshot)
        db.commit()

        # Run the task
        result = evaluate_alerts_task.apply(args=[None, snapshot.id]).result

        assert result["status"] == "success"
        assert result["items_processed"] == 1

        # Check that alert was created for group
        occurrences, _ = AlertOccurrenceService.list_occurrences(db)
        assert len(occurrences) == 1
        assert occurrences[0].policy_id == policy.id
        assert occurrences[0].group_id == group.id
        assert occurrences[0].current_value == 80.0
        assert occurrences[0].threshold_value == 85.0