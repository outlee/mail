import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from worker.celery_app import app
from worker.config import get_settings
from worker.database import SessionLocal

from app.models import CSVImportType, TaskRunStatus
from app.services import (
    AssetService,
    CSVImportJobService,
    FailureEventService,
    GroupService,
    KPIService,
    RuntimeCounterService,
    TaskRunService,
)

logger = logging.getLogger(__name__)
settings = get_settings()

IMPORT_REQUIRED_COLUMNS: Dict[CSVImportType, Set[str]] = {
    CSVImportType.ASSETS: {"external_id", "name"},
    CSVImportType.RUNTIME: {"asset_external_id", "counter_name", "value", "recorded_at"},
    CSVImportType.FAILURES: {"asset_external_id", "failure_code", "occurred_at"},
}


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized_key = key.strip().lower()
        if isinstance(value, str):
            value = value.strip()
        normalized[normalized_key] = value
    return normalized


def _parse_datetime(value: Any) -> datetime:
    if value is None or value == "":
        raise ValueError("datetime value is required")
    normalized = str(value).strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid datetime format: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_float(value: Any, field_name: str) -> float:
    if value in (None, ""):
        raise ValueError(f"{field_name} is required")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a numeric value") from exc


def _parse_metadata(value: Any) -> Optional[Dict[str, Any]]:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("metadata must be valid JSON") from exc


def _natural_key(import_type: CSVImportType, row: Dict[str, Any]) -> Tuple[str, ...]:
    if import_type == CSVImportType.ASSETS:
        return (row.get("external_id") or "",)
    if import_type == CSVImportType.RUNTIME:
        return (
            row.get("asset_external_id") or "",
            row.get("counter_name") or "",
            row.get("recorded_at") or "",
        )
    if import_type == CSVImportType.FAILURES:
        return (
            row.get("asset_external_id") or "",
            row.get("failure_code") or "",
            row.get("occurred_at") or "",
        )
    raise ValueError(f"Unsupported import type: {import_type}")


def _process_row(import_type: CSVImportType, row: Dict[str, Any], db) -> None:
    if import_type == CSVImportType.ASSETS:
        external_id = row.get("external_id")
        name = row.get("name")
        if not external_id:
            raise ValueError("external_id is required")
        if not name:
            raise ValueError("name is required")
        description = row.get("description") or None
        AssetService.upsert_asset(
            db=db,
            external_id=external_id,
            name=name,
            description=description,
        )
        return

    if import_type == CSVImportType.RUNTIME:
        asset_external_id = row.get("asset_external_id")
        if not asset_external_id:
            raise ValueError("asset_external_id is required")
        asset = AssetService.get_asset_by_external_id(db, asset_external_id)
        if not asset:
            raise ValueError(
                f"Asset with external_id '{asset_external_id}' does not exist"
            )
        counter_name = row.get("counter_name")
        if not counter_name:
            raise ValueError("counter_name is required")
        value = _parse_float(row.get("value"), "value")
        recorded_at = _parse_datetime(row.get("recorded_at"))
        metadata = _parse_metadata(row.get("metadata"))
        RuntimeCounterService.upsert_counter(
            db=db,
            asset_id=asset.id,
            counter_name=counter_name,
            recorded_at=recorded_at,
            value=value,
            metadata=metadata,
        )
        return

    if import_type == CSVImportType.FAILURES:
        asset_external_id = row.get("asset_external_id")
        if not asset_external_id:
            raise ValueError("asset_external_id is required")
        asset = AssetService.get_asset_by_external_id(db, asset_external_id)
        if not asset:
            raise ValueError(
                f"Asset with external_id '{asset_external_id}' does not exist"
            )
        failure_code = row.get("failure_code")
        if not failure_code:
            raise ValueError("failure_code is required")
        occurred_at = _parse_datetime(row.get("occurred_at"))
        resolved_at_raw = row.get("resolved_at")
        resolved_at = _parse_datetime(resolved_at_raw) if resolved_at_raw else None
        description = row.get("description") or None
        metadata = _parse_metadata(row.get("metadata"))
        FailureEventService.upsert_event(
            db=db,
            asset_id=asset.id,
            failure_code=failure_code,
            occurred_at=occurred_at,
            description=description,
            resolved_at=resolved_at,
            metadata=metadata,
        )
        return

    raise ValueError(f"Unsupported import type: {import_type}")


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
    name="worker.tasks.process_csv_import_task",
    bind=True,
    retry_kwargs={"max_retries": 0},
)
def process_csv_import_task(self, job_id: str):
    db = SessionLocal()
    errors: list[Dict[str, Any]] = []
    total_rows = 0
    processed_rows = 0
    skipped_rows = 0
    error_rows = 0

    try:
        job = CSVImportJobService.mark_processing(db, job_id)
        if not job:
            logger.error("CSV import job %s not found", job_id)
            return {"status": "not_found", "job_id": job_id}

        import_type = job.import_type
        required_columns = IMPORT_REQUIRED_COLUMNS.get(import_type)
        if not required_columns:
            raise ValueError(f"Unsupported import type: {import_type}")

        csv_path = Path(job.storage_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found at {job.storage_path}")

        with csv_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV file is missing a header row")

            header_columns = {col.strip().lower() for col in reader.fieldnames if col}
            missing_columns = required_columns - header_columns
            if missing_columns:
                raise ValueError(
                    "Missing required columns: "
                    + ", ".join(sorted(missing_columns))
                )

            seen_keys: Set[Tuple[str, ...]] = set()

            for row_number, raw_row in enumerate(reader, start=1):
                normalized_row = _normalize_row(raw_row)
                if not any(value not in (None, "") for value in normalized_row.values()):
                    continue

                total_rows += 1

                try:
                    for column in required_columns:
                        if normalized_row.get(column) in (None, ""):
                            raise ValueError(f"{column} is required")

                    natural_key = _natural_key(import_type, normalized_row)
                    if natural_key in seen_keys:
                        raise ValueError(
                            "Duplicate entry detected for natural key "
                            + "|".join(natural_key)
                        )

                    _process_row(import_type, normalized_row, db)
                    seen_keys.add(natural_key)
                    processed_rows += 1
                except Exception as row_exc:
                    db.rollback()
                    skipped_rows += 1
                    error_rows += 1
                    if len(errors) < settings.csv_import_error_sample_size:
                        errors.append(
                            {
                                "row_number": row_number,
                                "error": str(row_exc),
                                "row": normalized_row,
                            }
                        )
                    logger.warning(
                        "Import job %s: row %s failed validation: %s",
                        job_id,
                        row_number,
                        row_exc,
                    )

        message = None
        if error_rows and processed_rows:
            message = f"Completed with {error_rows} errors"

        if processed_rows == 0 and error_rows:
            CSVImportJobService.mark_failed(
                db=db,
                job_id=job_id,
                total_rows=total_rows,
                processed_rows=processed_rows,
                skipped_rows=skipped_rows,
                error_rows=error_rows,
                error_sample=errors,
                message="Import failed: no valid rows processed",
            )
            return {
                "status": "failed",
                "processed_rows": processed_rows,
                "error_rows": error_rows,
            }

        CSVImportJobService.mark_completed(
            db=db,
            job_id=job_id,
            total_rows=total_rows,
            processed_rows=processed_rows,
            skipped_rows=skipped_rows,
            error_rows=error_rows,
            error_sample=errors,
            message=message,
        )

        status_message = "completed_with_errors" if error_rows else "completed"
        return {
            "status": status_message,
            "processed_rows": processed_rows,
            "error_rows": error_rows,
        }

    except Exception as exc:
        logger.error("CSV import job %s failed: %s", job_id, exc, exc_info=True)
        db.rollback()
        CSVImportJobService.mark_failed(
            db=db,
            job_id=job_id,
            total_rows=total_rows,
            processed_rows=processed_rows,
            skipped_rows=skipped_rows,
            error_rows=error_rows or total_rows,
            error_sample=errors,
            message=str(exc),
        )
        raise
    finally:
        db.close()


@app.task(name="worker.tasks.example_task")
def example_task(x: int, y: int):
    logger.info(f"Running example task with x={x}, y={y}")
    result = x + y
    logger.info(f"Example task result: {result}")
    return result
