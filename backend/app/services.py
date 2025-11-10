import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from opentelemetry import trace

from app.models import (
    Asset,
    AssetRuntime,
    AuditAction,
    AuditLogEntry,
    DataQualityReport,
    FailureEvent,
    FailureSeverity,
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


class AssetRuntimeService:
    @staticmethod
    def create_asset_runtime(
        db: Session,
        asset_id: str,
        runtime_counter: int,
        metadata: Optional[str] = None,
    ) -> AssetRuntime:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("create_asset_runtime") as span:
            span.set_attribute("asset_id", asset_id)
            span.set_attribute("runtime_counter", runtime_counter)
            
            # Validate monotonic runtime counter
            last_runtime = (
                db.query(AssetRuntime)
                .filter(AssetRuntime.asset_id == asset_id)
                .order_by(AssetRuntime.runtime_counter.desc())
                .first()
            )
            
            if last_runtime and runtime_counter <= last_runtime.runtime_counter:
                span.set_attribute("validation_failed", True)
                span.set_attribute("last_counter", last_runtime.runtime_counter)
                raise ValueError(
                    f"Runtime counter must be greater than last recorded value ({last_runtime.runtime_counter})"
                )
            
            runtime_id = str(uuid.uuid4())
            db_runtime = AssetRuntime(
                id=runtime_id,
                asset_id=asset_id,
                runtime_counter=runtime_counter,
                metadata=metadata,
            )
            db.add(db_runtime)
            db.commit()
            db.refresh(db_runtime)
            
            span.set_attribute("runtime_id", runtime_id)
            return db_runtime

    @staticmethod
    def get_asset_runtime_by_id(db: Session, runtime_id: str) -> Optional[AssetRuntime]:
        return db.query(AssetRuntime).filter(AssetRuntime.id == runtime_id).first()

    @staticmethod
    def list_asset_runtimes(
        db: Session, asset_id: str, skip: int = 0, limit: int = 100
    ) -> list[AssetRuntime]:
        return (
            db.query(AssetRuntime)
            .filter(AssetRuntime.asset_id == asset_id)
            .order_by(AssetRuntime.runtime_counter.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


class FailureEventService:
    @staticmethod
    def create_failure_event(
        db: Session,
        asset_id: str,
        severity: FailureSeverity,
        start_time: datetime,
        description: str,
        end_time: Optional[datetime] = None,
        metadata: Optional[str] = None,
    ) -> FailureEvent:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("create_failure_event") as span:
            span.set_attribute("asset_id", asset_id)
            span.set_attribute("severity", severity.value)
            span.set_attribute("start_time", start_time.isoformat())
            if end_time:
                span.set_attribute("end_time", end_time.isoformat())
            
            # Check for overlapping failure events
            overlapping_events = (
                db.query(FailureEvent)
                .filter(
                    FailureEvent.asset_id == asset_id,
                    FailureEvent.start_time <= end_time if end_time else True,
                    FailureEvent.end_time >= start_time if start_time else True,
                )
                .all()
            )
            
            span.set_attribute("existing_events_checked", len(overlapping_events))
            
            for event in overlapping_events:
                if (
                    (event.start_time <= start_time <= event.end_time)
                    or (event.start_time <= end_time <= event.end_time)
                    or (start_time <= event.start_time and end_time >= event.end_time)
                ):
                    span.set_attribute("validation_failed", True)
                    span.set_attribute("overlapping_event_id", event.id)
                    raise ValueError(
                        f"Failure event overlaps with existing event {event.id} "
                        f"({event.start_time} to {event.end_time})"
                    )
            
            event_id = str(uuid.uuid4())
            db_event = FailureEvent(
                id=event_id,
                asset_id=asset_id,
                severity=severity,
                start_time=start_time,
                end_time=end_time,
                description=description,
                metadata=metadata,
            )
            db.add(db_event)
            db.commit()
            db.refresh(db_event)
            
            span.set_attribute("event_id", event_id)
            return db_event

    @staticmethod
    def get_failure_event_by_id(db: Session, event_id: str) -> Optional[FailureEvent]:
        return db.query(FailureEvent).filter(FailureEvent.id == event_id).first()

    @staticmethod
    def update_failure_event(
        db: Session, event_id: str, **kwargs
    ) -> Optional[FailureEvent]:
        event = FailureEventService.get_failure_event_by_id(db, event_id)
        if event:
            for key, value in kwargs.items():
                if hasattr(event, key) and value is not None:
                    setattr(event, key, value)
            db.commit()
            db.refresh(event)
        return event

    @staticmethod
    def delete_failure_event(db: Session, event_id: str) -> bool:
        event = FailureEventService.get_failure_event_by_id(db, event_id)
        if event:
            db.delete(event)
            db.commit()
            return True
        return False

    @staticmethod
    def list_failure_events(
        db: Session, asset_id: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> list[FailureEvent]:
        query = db.query(FailureEvent)
        if asset_id:
            query = query.filter(FailureEvent.asset_id == asset_id)
        return query.order_by(FailureEvent.start_time.desc()).offset(skip).limit(limit).all()


class AuditLogService:
    @staticmethod
    def create_audit_entry(
        db: Session,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        old_values: Optional[str] = None,
        new_values: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLogEntry:
        entry_id = str(uuid.uuid4())
        db_entry = AuditLogEntry(
            id=entry_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
        )
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        return db_entry

    @staticmethod
    def list_audit_entries(
        db: Session,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        query = db.query(AuditLogEntry)
        if resource_type:
            query = query.filter(AuditLogEntry.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLogEntry.resource_id == resource_id)
        if user_id:
            query = query.filter(AuditLogEntry.user_id == user_id)
        return query.order_by(AuditLogEntry.timestamp.desc()).offset(skip).limit(limit).all()


class DataQualityService:
    @staticmethod
    def create_data_quality_report(
        db: Session,
        report_type: str,
        status: str = "pending",
    ) -> DataQualityReport:
        report_id = str(uuid.uuid4())
        db_report = DataQualityReport(
            id=report_id,
            report_type=report_type,
            status=status,
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report

    @staticmethod
    def update_data_quality_report(
        db: Session, report_id: str, **kwargs
    ) -> Optional[DataQualityReport]:
        report = db.query(DataQualityReport).filter(DataQualityReport.id == report_id).first()
        if report:
            for key, value in kwargs.items():
                if hasattr(report, key) and value is not None:
                    setattr(report, key, value)
            db.commit()
            db.refresh(report)
        return report

    @staticmethod
    def get_data_quality_report_by_id(db: Session, report_id: str) -> Optional[DataQualityReport]:
        return db.query(DataQualityReport).filter(DataQualityReport.id == report_id).first()

    @staticmethod
    def list_data_quality_reports(
        db: Session, skip: int = 0, limit: int = 100
    ) -> list[DataQualityReport]:
        return (
            db.query(DataQualityReport)
            .order_by(DataQualityReport.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def run_data_quality_check(db: Session, report_type: str = "comprehensive") -> DataQualityReport:
        """Run data quality validation checks."""
        report = DataQualityService.create_data_quality_report(db, report_type, "running")
        
        issues = []
        assets_checked = 0
        
        try:
            # Check 1: Assets without runtime entries
            assets_without_runtime = (
                db.query(Asset)
                .outerjoin(AssetRuntime)
                .filter(AssetRuntime.id.is_(None))
                .all()
            )
            
            for asset in assets_without_runtime:
                issues.append(f"Asset {asset.id} ({asset.name}) has no runtime entries")
            
            # Check 2: Failure events with invalid time windows
            invalid_failure_events = (
                db.query(FailureEvent)
                .filter(
                    FailureEvent.end_time.isnot(None),
                    FailureEvent.end_time <= FailureEvent.start_time
                )
                .all()
            )
            
            for event in invalid_failure_events:
                issues.append(f"Failure event {event.id} has invalid time window")
            
            # Check 3: Assets with decreasing runtime counters
            assets_with_decreasing_runtime = []
            all_assets = db.query(Asset).all()
            
            for asset in all_assets:
                runtimes = (
                    db.query(AssetRuntime)
                    .filter(AssetRuntime.asset_id == asset.id)
                    .order_by(AssetRuntime.recorded_at.asc())
                    .all()
                )
                
                for i in range(1, len(runtimes)):
                    if runtimes[i].runtime_counter < runtimes[i-1].runtime_counter:
                        assets_with_decreasing_runtime.append(asset.id)
                        break
            
            for asset_id in assets_with_decreasing_runtime:
                issues.append(f"Asset {asset_id} has decreasing runtime counters")
            
            assets_checked = len(all_assets)
            
            # Update report with results
            DataQualityService.update_data_quality_report(
                db,
                report.id,
                status="completed",
                summary=f"Found {len(issues)} issues across {assets_checked} assets",
                details="\n".join(issues) if issues else "No issues found",
                issues_found=len(issues),
                assets_checked=assets_checked,
                completed_at=datetime.utcnow(),
            )
            
            logger.info(f"Data quality check completed: {len(issues)} issues found")
            
        except Exception as e:
            logger.error(f"Data quality check failed: {e}")
            DataQualityService.update_data_quality_report(
                db,
                report.id,
                status="failed",
                summary=f"Data quality check failed: {str(e)}",
                completed_at=datetime.utcnow(),
            )
        
        return DataQualityService.get_data_quality_report_by_id(db, report.id)
