import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    Asset,
    CSVImportJob,
    CSVImportStatus,
    CSVImportType,
    FailureEvent,
    Group,
    KPISnapshot,
    RefreshToken,
    RuntimeCounter,
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
    def create_asset(
        db: Session,
        name: str,
        description: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> Asset:
        asset_id = str(uuid.uuid4())
        external_id = external_id or str(uuid.uuid4())
        db_asset = Asset(
            id=asset_id,
            external_id=external_id,
            name=name,
            description=description,
        )
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)
        return db_asset

    @staticmethod
    def upsert_asset(
        db: Session,
        external_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> Asset:
        asset = (
            db.query(Asset)
            .filter(Asset.external_id == external_id)
            .first()
        )

        if asset:
            asset.name = name
            asset.description = description
        else:
            asset = Asset(
                id=str(uuid.uuid4()),
                external_id=external_id,
                name=name,
                description=description,
            )
            db.add(asset)

        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def get_asset_by_id(db: Session, asset_id: str) -> Optional[Asset]:
        return db.query(Asset).filter(Asset.id == asset_id).first()

    @staticmethod
    def get_asset_by_external_id(db: Session, external_id: str) -> Optional[Asset]:
        return db.query(Asset).filter(Asset.external_id == external_id).first()

    @staticmethod
    def list_assets(db: Session, skip: int = 0, limit: int = 100) -> list[Asset]:
        return db.query(Asset).offset(skip).limit(limit).all()


class GroupService:
    @staticmethod
    def create_group(
        db: Session,
        name: str,
        description: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> Group:
        group_id = str(uuid.uuid4())
        db_group = Group(
            id=group_id,
            external_id=external_id,
            name=name,
            description=description,
        )
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


class RuntimeCounterService:
    @staticmethod
    def upsert_counter(
        db: Session,
        asset_id: str,
        counter_name: str,
        recorded_at: datetime,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RuntimeCounter:
        counter = (
            db.query(RuntimeCounter)
            .filter(
                RuntimeCounter.asset_id == asset_id,
                RuntimeCounter.counter_name == counter_name,
                RuntimeCounter.recorded_at == recorded_at,
            )
            .first()
        )

        if counter:
            counter.value = value
            counter.metadata_json = metadata
            counter.updated_at = datetime.utcnow()
        else:
            counter = RuntimeCounter(
                id=str(uuid.uuid4()),
                asset_id=asset_id,
                counter_name=counter_name,
                recorded_at=recorded_at,
                value=value,
                metadata_json=metadata,
            )
            db.add(counter)

        db.commit()
        db.refresh(counter)
        return counter


class FailureEventService:
    @staticmethod
    def upsert_event(
        db: Session,
        asset_id: str,
        failure_code: str,
        occurred_at: datetime,
        description: Optional[str] = None,
        resolved_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FailureEvent:
        event = (
            db.query(FailureEvent)
            .filter(
                FailureEvent.asset_id == asset_id,
                FailureEvent.failure_code == failure_code,
                FailureEvent.occurred_at == occurred_at,
            )
            .first()
        )

        if event:
            event.description = description
            event.metadata_json = metadata
            event.resolved_at = resolved_at
            event.updated_at = datetime.utcnow()
        else:
            event = FailureEvent(
                id=str(uuid.uuid4()),
                asset_id=asset_id,
                failure_code=failure_code,
                occurred_at=occurred_at,
                description=description,
                resolved_at=resolved_at,
                metadata_json=metadata,
            )
            db.add(event)

        db.commit()
        db.refresh(event)
        return event


class CSVImportJobService:
    @staticmethod
    def create_job(
        db: Session,
        import_type: CSVImportType,
        idempotency_key: str,
        storage_path: str,
        actor_id: Optional[str] = None,
        source_filename: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> CSVImportJob:
        job = CSVImportJob(
            id=job_id or str(uuid.uuid4()),
            import_type=import_type,
            idempotency_key=idempotency_key,
            storage_path=storage_path,
            actor_id=actor_id,
            source_filename=source_filename,
            error_sample=[],
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[CSVImportJob]:
        return db.query(CSVImportJob).filter(CSVImportJob.id == job_id).first()

    @staticmethod
    def get_by_idempotency(
        db: Session, import_type: CSVImportType, idempotency_key: str
    ) -> Optional[CSVImportJob]:
        return (
            db.query(CSVImportJob)
            .filter(
                CSVImportJob.import_type == import_type,
                CSVImportJob.idempotency_key == idempotency_key,
            )
            .order_by(CSVImportJob.created_at.desc())
            .first()
        )

    @staticmethod
    def is_within_ttl(job: CSVImportJob, ttl_minutes: int) -> bool:
        if ttl_minutes <= 0:
            return False
        cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
        return job.created_at >= cutoff

    @staticmethod
    def mark_processing(db: Session, job_id: str) -> Optional[CSVImportJob]:
        job = CSVImportJobService.get_job(db, job_id)
        if job:
            job.status = CSVImportStatus.PROCESSING
            job.started_at = datetime.utcnow()
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def mark_completed(
        db: Session,
        job_id: str,
        total_rows: int,
        processed_rows: int,
        skipped_rows: int,
        error_rows: int,
        error_sample: Optional[list[Dict[str, Any]]] = None,
        message: Optional[str] = None,
    ) -> Optional[CSVImportJob]:
        job = CSVImportJobService.get_job(db, job_id)
        if job:
            job.status = CSVImportStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.total_rows = total_rows
            job.processed_rows = processed_rows
            job.skipped_rows = skipped_rows
            job.error_rows = error_rows
            job.error_sample = error_sample or []
            job.message = message
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def mark_failed(
        db: Session,
        job_id: str,
        total_rows: int,
        processed_rows: int,
        skipped_rows: int,
        error_rows: int,
        error_sample: Optional[list[Dict[str, Any]]] = None,
        message: Optional[str] = None,
    ) -> Optional[CSVImportJob]:
        job = CSVImportJobService.get_job(db, job_id)
        if job:
            job.status = CSVImportStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.total_rows = total_rows
            job.processed_rows = processed_rows
            job.skipped_rows = skipped_rows
            job.error_rows = error_rows
            job.error_sample = error_sample or []
            job.message = message
            db.commit()
            db.refresh(job)
        return job


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
            items_processed=0,
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
