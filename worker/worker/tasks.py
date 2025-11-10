import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from worker.celery_app import app
from worker.config import get_settings
from worker.database import SessionLocal

from app.models import TaskRunStatus
from app.services import (
    AssetService,
    DataQualityService,
    GroupService,
    KPIService,
    TaskRunService,
)

logger = logging.getLogger(__name__)
settings = get_settings()


@app.task(name="worker.tasks.heartbeat_task")
def heartbeat_task():
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"Worker heartbeat at {timestamp}")
    return {"status": "alive", "timestamp": timestamp}


@app.task(
    name="worker.tasks.recompute_rolling_kpis_task",
    bind=True,
    retry_kwargs={"max_retries": 3},
    default_retry_delay=10,
)
def recompute_rolling_kpis_task(
    self,
    task_run_id: Optional[str],
    scope: str,
    target_id: Optional[str],
):
    db = SessionLocal()
    task_run = None

    try:
        logger.info(
            f"Starting rolling KPI recomputation task: "
            f"task_run_id={task_run_id}, scope={scope}, target_id={target_id}"
        )

        if task_run_id:
            task_run = TaskRunService.get_task_run(db, task_run_id)
            if task_run:
                TaskRunService.start_task_run(db, task_run_id)

        items_processed = 0

        if scope == "all":
            assets = AssetService.list_assets(db, limit=10000)
            for asset in assets:
                try:
                    success = KPIService.recompute_asset_kpis(
                        db, asset.id, kpi_type="rolling", task_run_id=task_run_id
                    )
                    if success:
                        items_processed += 1
                except Exception as e:
                    logger.error(f"Error recomputing KPI for asset {asset.id}: {e}")
                    continue

        elif scope == "asset" and target_id:
            success = KPIService.recompute_asset_kpis(
                db, target_id, kpi_type="rolling", task_run_id=task_run_id
            )
            if success:
                items_processed = 1

        if task_run_id:
            TaskRunService.update_task_run(
                db=db,
                task_run_id=task_run_id,
                status=TaskRunStatus.SUCCESS,
                completed_at=datetime.utcnow(),
                items_processed=items_processed,
            )

        logger.info(
            f"Rolling KPI recomputation completed: "
            f"processed {items_processed} items"
        )

        return {
            "status": "success",
            "items_processed": items_processed,
        }

    except Exception as e:
        logger.error(f"Error in rolling KPI recomputation: {e}", exc_info=True)

        if task_run_id:
            try:
                TaskRunService.update_task_run(
                    db=db,
                    task_run_id=task_run_id,
                    status=TaskRunStatus.FAILED,
                    completed_at=datetime.utcnow(),
                    error_message=str(e),
                )
            except Exception as update_error:
                logger.error(f"Failed to update task run on error: {update_error}")

        raise self.retry(exc=e)

    finally:
        db.close()


@app.task(
    name="worker.tasks.recompute_calendar_kpis_task",
    bind=True,
    retry_kwargs={"max_retries": 3},
    default_retry_delay=10,
)
def recompute_calendar_kpis_task(
    self,
    task_run_id: Optional[str],
    scope: str,
    target_id: Optional[str],
):
    db = SessionLocal()
    task_run = None

    try:
        logger.info(
            f"Starting calendar KPI recomputation task: "
            f"task_run_id={task_run_id}, scope={scope}, target_id={target_id}"
        )

        if task_run_id:
            task_run = TaskRunService.get_task_run(db, task_run_id)
            if task_run:
                TaskRunService.start_task_run(db, task_run_id)

        items_processed = 0

        if scope == "all":
            groups = GroupService.list_groups(db, limit=10000)
            for group in groups:
                try:
                    success = KPIService.recompute_group_kpis(
                        db, group.id, kpi_type="calendar", task_run_id=task_run_id
                    )
                    if success:
                        items_processed += 1
                except Exception as e:
                    logger.error(f"Error recomputing KPI for group {group.id}: {e}")
                    continue

        elif scope == "group" and target_id:
            success = KPIService.recompute_group_kpis(
                db, target_id, kpi_type="calendar", task_run_id=task_run_id
            )
            if success:
                items_processed = 1

        if task_run_id:
            TaskRunService.update_task_run(
                db=db,
                task_run_id=task_run_id,
                status=TaskRunStatus.SUCCESS,
                completed_at=datetime.utcnow(),
                items_processed=items_processed,
            )

        logger.info(
            f"Calendar KPI recomputation completed: "
            f"processed {items_processed} items"
        )

        return {
            "status": "success",
            "items_processed": items_processed,
        }

    except Exception as e:
        logger.error(f"Error in calendar KPI recomputation: {e}", exc_info=True)

        if task_run_id:
            try:
                TaskRunService.update_task_run(
                    db=db,
                    task_run_id=task_run_id,
                    status=TaskRunStatus.FAILED,
                    completed_at=datetime.utcnow(),
                    error_message=str(e),
                )
            except Exception as update_error:
                logger.error(f"Failed to update task run on error: {update_error}")

        raise self.retry(exc=e)

    finally:
        db.close()


@app.task(
    name="worker.tasks.data_quality_check_task",
    bind=True,
    retry_kwargs={"max_retries": 3},
    default_retry_delay=10,
)
def data_quality_check_task(
    self,
    task_run_id: Optional[str],
    report_type: str = "comprehensive",
):
    db = SessionLocal()
    task_run = None
    start_time = time.time()

    try:
        logger.info(
            f"Starting data quality check task: "
            f"task_run_id={task_run_id}, report_type={report_type}"
        )

        if task_run_id:
            task_run = TaskRunService.get_task_run(db, task_run_id)
            if task_run:
                TaskRunService.start_task_run(db, task_run_id)

        # Run data quality check
        report = DataQualityService.run_data_quality_check(db, report_type)
        
        items_processed = 1  # One report generated
        duration = time.time() - start_time

        # Record metrics (if available)
        try:
            from app.metrics import record_task_execution
            record_task_execution(
                task_name="data_quality_check",
                status="success",
                duration=duration
            )
        except ImportError:
            # Metrics not available in worker environment
            pass

        if task_run_id:
            TaskRunService.update_task_run(
                db=db,
                task_run_id=task_run_id,
                status=TaskRunStatus.SUCCESS,
                completed_at=datetime.utcnow(),
                items_processed=items_processed,
            )

        logger.info(
            f"Data quality check completed: "
            f"report_id={report.id}, issues_found={report.issues_found}"
        )

        return {
            "status": "success",
            "report_id": report.id,
            "issues_found": report.issues_found,
            "assets_checked": report.assets_checked,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error in data quality check: {e}", exc_info=True)

        # Record failure metrics
        try:
            from app.metrics import record_task_execution
            record_task_execution(
                task_name="data_quality_check",
                status="failed",
                duration=duration,
                error_type=type(e).__name__
            )
        except ImportError:
            # Metrics not available in worker environment
            pass

        if task_run_id:
            try:
                TaskRunService.update_task_run(
                    db=db,
                    task_run_id=task_run_id,
                    status=TaskRunStatus.FAILED,
                    completed_at=datetime.utcnow(),
                    error_message=str(e),
                )
            except Exception as update_error:
                logger.error(f"Failed to update task run on error: {update_error}")

        raise self.retry(exc=e)

    finally:
        db.close()


@app.task(name="worker.tasks.example_task")
def example_task(x: int, y: int):
    logger.info(f"Running example task with x={x}, y={y}")
    result = x + y
    logger.info(f"Example task result: {result}")
    return result
