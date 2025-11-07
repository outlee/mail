import json
import logging
import smtplib
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    AlertComparator,
    AlertEventLog,
    AlertOccurrence,
    AlertPolicy,
    AlertSeverity,
    AlertStatus,
    Asset,
    Group,
    KPISnapshot,
    RefreshToken,
    TaskRun,
    TaskRunStatus,
    User,
    UserRole,
)
from app.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    def create_user(
        db: Session,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.OPERATOR,
    ) -> User:
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(password)
        db_user = User(
            id=user_id,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def authenticate_user(
        db: Session, email: str, password: str
    ) -> Optional[User]:
        user = UserService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


class RefreshTokenService:
    @staticmethod
    def create_refresh_token(
        db: Session, user_id: str, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token_id = str(uuid.uuid4())
        db_token = RefreshToken(
            id=token_id, user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        db.add(db_token)
        db.commit()
        db.refresh(db_token)
        return db_token

    @staticmethod
    def get_refresh_token(
        db: Session, token_hash: str
    ) -> Optional[RefreshToken]:
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.utcnow(),
            )
            .first()
        )

    @staticmethod
    def revoke_refresh_token(db: Session, token_id: str) -> bool:
        token = db.query(RefreshToken).filter(RefreshToken.id == token_id).first()
        if token:
            token.revoked = True
            db.commit()
            return True
        return False


class AssetService:
    @staticmethod
    def create_asset(db: Session, name: str, description: Optional[str] = None) -> Asset:
        asset_id = str(uuid.uuid4())
        db_asset = Asset(id=asset_id, name=name, description=description)
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)
        return db_asset

    @staticmethod
    def get_asset_by_id(db: Session, asset_id: str) -> Optional[Asset]:
        return db.query(Asset).filter(Asset.id == asset_id).first()

    @staticmethod
    def list_assets(db: Session, skip: int = 0, limit: int = 100) -> list[Asset]:
        return db.query(Asset).offset(skip).limit(limit).all()


class GroupService:
    @staticmethod
    def create_group(db: Session, name: str, description: Optional[str] = None) -> Group:
        group_id = str(uuid.uuid4())
        db_group = Group(id=group_id, name=name, description=description)
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        return db_group

    @staticmethod
    def get_group_by_id(db: Session, group_id: str) -> Optional[Group]:
        return db.query(Group).filter(Group.id == group_id).first()

    @staticmethod
    def list_groups(db: Session, skip: int = 0, limit: int = 100) -> list[Group]:
        return db.query(Group).offset(skip).limit(limit).all()


class KPIService:
    LOCK_TIMEOUT = 30

    @staticmethod
    def acquire_lock(db: Session, lock_id: str) -> bool:
        try:
            db.execute(text(f"SELECT pg_advisory_lock('{lock_id}'::bigint)"))
            return True
        except Exception as e:
            logger.error(f"Failed to acquire lock {lock_id}: {e}")
            return False

    @staticmethod
    def release_lock(db: Session, lock_id: str) -> bool:
        try:
            db.execute(text(f"SELECT pg_advisory_unlock('{lock_id}'::bigint)"))
            return True
        except Exception as e:
            logger.error(f"Failed to release lock {lock_id}: {e}")
            return False

    @staticmethod
    def _generate_lock_id(prefix: str, target_id: str) -> str:
        combined = f"{prefix}:{target_id}".encode()
        import hashlib
        hash_obj = hashlib.md5(combined)
        return str(int(hash_obj.hexdigest(), 16) % (2**63 - 1))

    @staticmethod
    def recompute_asset_kpis(
        db: Session,
        asset_id: str,
        kpi_type: str = "rolling",
        task_run_id: Optional[str] = None,
    ) -> bool:
        lock_id = KPIService._generate_lock_id("kpi", asset_id)

        if not KPIService.acquire_lock(db, lock_id):
            logger.warning(f"Could not acquire lock for asset {asset_id}")
            return False

        try:
            asset = AssetService.get_asset_by_id(db, asset_id)
            if not asset:
                logger.warning(f"Asset {asset_id} not found")
                return False

            now = datetime.utcnow()
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)

            value = 95.0

            snapshot_id = str(uuid.uuid4())
            snapshot = KPISnapshot(
                id=snapshot_id,
                asset_id=asset_id,
                kpi_type=kpi_type,
                value=value,
                period_start=period_start,
                period_end=period_end,
            )
            db.add(snapshot)
            db.commit()

            # Trigger alert evaluation for the new snapshot
            try:
                from worker.celery_app import app as celery_app
                celery_app.send_task(
                    "worker.tasks.evaluate_alerts_task",
                    args=[None, snapshot_id]
                )
                logger.info(f"Triggered alert evaluation for asset {asset_id} snapshot {snapshot_id}")
            except Exception as e:
                logger.warning(f"Failed to trigger alert evaluation for asset {asset_id}: {e}")

            logger.info(f"Recomputed KPI for asset {asset_id}: {value}")
            return True

        except Exception as e:
            logger.error(f"Error recomputing KPI for asset {asset_id}: {e}")
            return False
        finally:
            KPIService.release_lock(db, lock_id)

    @staticmethod
    def recompute_group_kpis(
        db: Session,
        group_id: str,
        kpi_type: str = "rolling",
        task_run_id: Optional[str] = None,
    ) -> bool:
        lock_id = KPIService._generate_lock_id("kpi_group", group_id)

        if not KPIService.acquire_lock(db, lock_id):
            logger.warning(f"Could not acquire lock for group {group_id}")
            return False

        try:
            group = GroupService.get_group_by_id(db, group_id)
            if not group:
                logger.warning(f"Group {group_id} not found")
                return False

            now = datetime.utcnow()
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)

            value = 92.0

            snapshot_id = str(uuid.uuid4())
            snapshot = KPISnapshot(
                id=snapshot_id,
                group_id=group_id,
                kpi_type=kpi_type,
                value=value,
                period_start=period_start,
                period_end=period_end,
            )
            db.add(snapshot)
            db.commit()

            # Trigger alert evaluation for new snapshot
            try:
                from worker.celery_app import app as celery_app
                celery_app.send_task(
                    "worker.tasks.evaluate_alerts_task",
                    args=[None, snapshot_id]
                )
                logger.info(f"Triggered alert evaluation for group {group_id} snapshot {snapshot_id}")
            except Exception as e:
                logger.warning(f"Failed to trigger alert evaluation for group {group_id}: {e}")

            logger.info(f"Recomputed KPI for group {group_id}: {value}")
            return True

        except Exception as e:
            logger.error(f"Error recomputing KPI for group {group_id}: {e}")
            return False
        finally:
            KPIService.release_lock(db, lock_id)


class TaskRunService:
    @staticmethod
    def create_task_run(
        db: Session,
        task_name: str,
        scope: Optional[str] = None,
        asset_id: Optional[str] = None,
        group_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> TaskRun:
        run_id = str(uuid.uuid4())
        task_run = TaskRun(
            id=run_id,
            task_name=task_name,
            task_id=task_id,
            status=TaskRunStatus.PENDING,
            scope=scope,
            asset_id=asset_id,
            group_id=group_id,
        )
        db.add(task_run)
        db.commit()
        db.refresh(task_run)
        return task_run

    @staticmethod
    def get_task_run(db: Session, task_run_id: str) -> Optional[TaskRun]:
        return db.query(TaskRun).filter(TaskRun.id == task_run_id).first()

    @staticmethod
    def update_task_run(
        db: Session,
        task_run_id: str,
        status: TaskRunStatus,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        items_processed: int = 0,
    ) -> Optional[TaskRun]:
        task_run = TaskRunService.get_task_run(db, task_run_id)
        if task_run:
            task_run.status = status
            if completed_at:
                task_run.completed_at = completed_at
            if error_message:
                task_run.error_message = error_message
            task_run.items_processed = items_processed
            db.commit()
            db.refresh(task_run)
        return task_run

    @staticmethod
    def start_task_run(db: Session, task_run_id: str) -> Optional[TaskRun]:
        task_run = TaskRunService.get_task_run(db, task_run_id)
        if task_run:
            task_run.status = TaskRunStatus.RUNNING
            task_run.started_at = datetime.utcnow()
            db.commit()
            db.refresh(task_run)
        return task_run

    @staticmethod
    def list_task_runs(
        db: Session, skip: int = 0, limit: int = 100, task_name: Optional[str] = None
    ) -> list[TaskRun]:
        query = db.query(TaskRun)
        if task_name:
            query = query.filter(TaskRun.task_name == task_name)
        return query.order_by(TaskRun.created_at.desc()).offset(skip).limit(limit).all()


class AlertPolicyService:
    @staticmethod
    def create_policy(
        db: Session,
        name: str,
        description: Optional[str],
        metric_name: str,
        comparator: AlertComparator,
        threshold: float,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        deduplication_window_minutes: int = 60,
        email_recipients: Optional[list[str]] = None,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        is_active: bool = True,
    ) -> AlertPolicy:
        policy_id = str(uuid.uuid4())
        db_policy = AlertPolicy(
            id=policy_id,
            name=name,
            description=description,
            metric_name=metric_name,
            comparator=comparator,
            threshold=threshold,
            severity=severity,
            deduplication_window_minutes=deduplication_window_minutes,
            email_recipients=json.dumps(email_recipients) if email_recipients else None,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            is_active=is_active,
        )
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)
        return db_policy

    @staticmethod
    def get_policy_by_id(db: Session, policy_id: str) -> Optional[AlertPolicy]:
        return db.query(AlertPolicy).filter(AlertPolicy.id == policy_id).first()

    @staticmethod
    def get_policy_by_name(db: Session, name: str) -> Optional[AlertPolicy]:
        return db.query(AlertPolicy).filter(AlertPolicy.name == name).first()

    @staticmethod
    def list_policies(
        db: Session, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> list[AlertPolicy]:
        query = db.query(AlertPolicy)
        if active_only:
            query = query.filter(AlertPolicy.is_active == True)
        return query.order_by(AlertPolicy.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_policy(
        db: Session, policy_id: str, **kwargs
    ) -> Optional[AlertPolicy]:
        policy = AlertPolicyService.get_policy_by_id(db, policy_id)
        if not policy:
            return None

        if 'email_recipients' in kwargs and kwargs['email_recipients'] is not None:
            kwargs['email_recipients'] = json.dumps(kwargs['email_recipients'])

        for key, value in kwargs.items():
            if hasattr(policy, key) and value is not None:
                setattr(policy, key, value)

        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def delete_policy(db: Session, policy_id: str) -> bool:
        policy = AlertPolicyService.get_policy_by_id(db, policy_id)
        if policy:
            db.delete(policy)
            db.commit()
            return True
        return False


class AlertOccurrenceService:
    @staticmethod
    def create_occurrence(
        db: Session,
        policy_id: str,
        asset_id: Optional[str],
        group_id: Optional[str],
        kpi_snapshot_id: str,
        severity: AlertSeverity,
        current_value: float,
        threshold_value: float,
        message: str,
    ) -> AlertOccurrence:
        occurrence_id = str(uuid.uuid4())
        db_occurrence = AlertOccurrence(
            id=occurrence_id,
            policy_id=policy_id,
            asset_id=asset_id,
            group_id=group_id,
            kpi_snapshot_id=kpi_snapshot_id,
            status=AlertStatus.ACTIVE,
            severity=severity,
            current_value=current_value,
            threshold_value=threshold_value,
            message=message,
        )
        db.add(db_occurrence)
        db.commit()
        db.refresh(db_occurrence)
        return db_occurrence

    @staticmethod
    def get_occurrence_by_id(db: Session, occurrence_id: str) -> Optional[AlertOccurrence]:
        return db.query(AlertOccurrence).filter(AlertOccurrence.id == occurrence_id).first()

    @staticmethod
    def list_occurrences(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        asset_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> tuple[list[AlertOccurrence], int]:
        query = db.query(AlertOccurrence)
        
        if status:
            query = query.filter(AlertOccurrence.status == status)
        if severity:
            query = query.filter(AlertOccurrence.severity == severity)
        if asset_id:
            query = query.filter(AlertOccurrence.asset_id == asset_id)
        if group_id:
            query = query.filter(AlertOccurrence.group_id == group_id)

        total = query.count()
        occurrences = query.order_by(AlertOccurrence.created_at.desc()).offset(skip).limit(limit).all()
        
        return occurrences, total

    @staticmethod
    def acknowledge_alert(
        db: Session, occurrence_id: str, user_id: str, message: Optional[str] = None
    ) -> Optional[AlertOccurrence]:
        occurrence = AlertOccurrenceService.get_occurrence_by_id(db, occurrence_id)
        if occurrence and occurrence.status == AlertStatus.ACTIVE:
            occurrence.status = AlertStatus.ACKNOWLEDGED
            occurrence.acknowledged_at = datetime.utcnow()
            occurrence.acknowledged_by = user_id
            db.commit()
            db.refresh(occurrence)
            
            # Log the acknowledgment
            AlertEventLogService.create_event_log(
                db, occurrence_id, "ACKNOWLEDGED", 
                f"Alert acknowledged by user {user_id}" + (f": {message}" if message else ""),
                user_id=user_id
            )
            
        return occurrence

    @staticmethod
    def resolve_alert(
        db: Session, occurrence_id: str, user_id: str, message: Optional[str] = None
    ) -> Optional[AlertOccurrence]:
        occurrence = AlertOccurrenceService.get_occurrence_by_id(db, occurrence_id)
        if occurrence and occurrence.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
            occurrence.status = AlertStatus.RESOLVED
            occurrence.resolved_at = datetime.utcnow()
            occurrence.resolved_by = user_id
            db.commit()
            db.refresh(occurrence)
            
            # Log the resolution
            AlertEventLogService.create_event_log(
                db, occurrence_id, "RESOLVED", 
                f"Alert resolved by user {user_id}" + (f": {message}" if message else ""),
                user_id=user_id
            )
            
        return occurrence

    @staticmethod
    def check_deduplication_window(
        db: Session, policy_id: str, asset_id: Optional[str], group_id: Optional[str], window_minutes: int
    ) -> bool:
        """Check if there's an active alert within the deduplication window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        query = db.query(AlertOccurrence).filter(
            AlertOccurrence.policy_id == policy_id,
            AlertOccurrence.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]),
            AlertOccurrence.created_at > cutoff_time
        )
        
        if asset_id:
            query = query.filter(AlertOccurrence.asset_id == asset_id)
        if group_id:
            query = query.filter(AlertOccurrence.group_id == group_id)
            
        return query.first() is not None


class AlertEventLogService:
    @staticmethod
    def create_event_log(
        db: Session,
        alert_occurrence_id: str,
        event_type: str,
        message: str,
        metadata: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> AlertEventLog:
        log_id = str(uuid.uuid4())
        db_log = AlertEventLog(
            id=log_id,
            alert_occurrence_id=alert_occurrence_id,
            event_type=event_type,
            message=message,
            metadata=json.dumps(metadata) if metadata else None,
            user_id=user_id,
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log

    @staticmethod
    def get_event_logs(
        db: Session, alert_occurrence_id: str, skip: int = 0, limit: int = 50
    ) -> list[AlertEventLog]:
        return (
            db.query(AlertEventLog)
            .filter(AlertEventLog.alert_occurrence_id == alert_occurrence_id)
            .order_by(AlertEventLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


class AlertEvaluationService:
    @staticmethod
    def evaluate_threshold(value: float, comparator: AlertComparator, threshold: float) -> bool:
        """Evaluate if a value crosses the threshold based on the comparator."""
        if comparator == AlertComparator.GREATER_THAN:
            return value > threshold
        elif comparator == AlertComparator.GREATER_THAN_OR_EQUAL:
            return value >= threshold
        elif comparator == AlertComparator.LESS_THAN:
            return value < threshold
        elif comparator == AlertComparator.LESS_THAN_OR_EQUAL:
            return value <= threshold
        elif comparator == AlertComparator.EQUAL:
            return value == threshold
        elif comparator == AlertComparator.NOT_EQUAL:
            return value != threshold
        return False

    @staticmethod
    def evaluate_policies_for_snapshot(
        db: Session, snapshot: KPISnapshot
    ) -> list[AlertOccurrence]:
        """Evaluate all active policies against a KPI snapshot."""
        triggered_alerts = []
        
        # Get active policies for the metric type
        policies = db.query(AlertPolicy).filter(
            AlertPolicy.is_active == True,
            AlertPolicy.metric_name == snapshot.kpi_type
        ).all()
        
        for policy in policies:
            # Check if threshold is crossed
            if AlertEvaluationService.evaluate_threshold(
                snapshot.value, policy.comparator, policy.threshold
            ):
                # Check deduplication window
                if not AlertOccurrenceService.check_deduplication_window(
                    db, policy.id, snapshot.asset_id, snapshot.group_id, policy.deduplication_window_minutes
                ):
                    # Create alert occurrence
                    message = f"{policy.metric_name} {policy.comparator.value} {policy.threshold} (current: {snapshot.value})"
                    
                    occurrence = AlertOccurrenceService.create_occurrence(
                        db=db,
                        policy_id=policy.id,
                        asset_id=snapshot.asset_id,
                        group_id=snapshot.group_id,
                        kpi_snapshot_id=snapshot.id,
                        severity=policy.severity,
                        current_value=snapshot.value,
                        threshold_value=policy.threshold,
                        message=message,
                    )
                    
                    # Log the trigger event
                    AlertEventLogService.create_event_log(
                        db, occurrence.id, "TRIGGERED", 
                        f"Alert triggered: {message}"
                    )
                    
                    triggered_alerts.append(occurrence)
                    
                    # Send notifications
                    AlertNotificationService.send_notifications(db, occurrence, policy)
        
        return triggered_alerts


class AlertNotificationService:
    @staticmethod
    def send_notifications(db: Session, occurrence: AlertOccurrence, policy: AlertPolicy) -> bool:
        """Send notifications for an alert occurrence."""
        success = True
        
        # Send email notifications
        if policy.email_recipients:
            try:
                email_success = AlertNotificationService._send_email_notification(occurrence, policy)
                if email_success:
                    occurrence.last_notification_at = datetime.utcnow()
                    db.commit()
                    
                    # Log notification
                    AlertEventLogService.create_event_log(
                        db, occurrence.id, "NOTIFIED", 
                        f"Email notifications sent to {policy.email_recipients}"
                    )
                else:
                    success = False
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
                success = False
        
        # Send webhook notification
        if policy.webhook_url:
            try:
                webhook_success = AlertNotificationService._send_webhook_notification(occurrence, policy)
                if webhook_success:
                    # Log notification
                    AlertEventLogService.create_event_log(
                        db, occurrence.id, "NOTIFIED", 
                        f"Webhook notification sent to {policy.webhook_url}"
                    )
                else:
                    success = False
            except Exception as e:
                logger.error(f"Failed to send webhook notification: {e}")
                success = False
        
        return success

    @staticmethod
    def _send_email_notification(occurrence: AlertOccurrence, policy: AlertPolicy) -> bool:
        """Send email notification (placeholder implementation)."""
        try:
            recipients = json.loads(policy.email_recipients) if policy.email_recipients else []
            if not recipients:
                return True
            
            # This is a placeholder - in a real implementation, you'd use SMTP settings
            # from config and a proper email template
            logger.info(f"Sending email alert to {recipients}: {occurrence.message}")
            
            # TODO: Implement actual email sending with SMTP
            # For now, we'll just log it
            return True
            
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False

    @staticmethod
    def _send_webhook_notification(occurrence: AlertOccurrence, policy: AlertPolicy) -> bool:
        """Send webhook notification (placeholder implementation)."""
        try:
            import hashlib
            import hmac
            
            # Prepare webhook payload
            payload = {
                "alert_id": occurrence.id,
                "policy_id": occurrence.policy_id,
                "policy_name": policy.name,
                "severity": occurrence.severity.value,
                "status": occurrence.status.value,
                "message": occurrence.message,
                "current_value": occurrence.current_value,
                "threshold_value": occurrence.threshold_value,
                "asset_id": occurrence.asset_id,
                "group_id": occurrence.group_id,
                "created_at": occurrence.created_at.isoformat(),
            }
            
            # Generate signature if secret is provided
            headers = {"Content-Type": "application/json"}
            if policy.webhook_secret:
                payload_str = json.dumps(payload, sort_keys=True)
                signature = hmac.new(
                    policy.webhook_secret.encode(),
                    payload_str.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Alert-Signature"] = f"sha256={signature}"
            
            # TODO: Implement actual HTTP request to webhook URL
            # For now, we'll just log it
            logger.info(f"Sending webhook to {policy.webhook_url}: {payload}")
            
            return True
            
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False
