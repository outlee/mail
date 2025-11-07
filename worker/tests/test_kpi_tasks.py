import sys
from pathlib import Path
from datetime import datetime
from unittest import mock

import pytest
from celery import Celery
from sqlalchemy.orm import Session

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.models import Asset, Group, KPISnapshot, TaskRun, TaskRunStatus
from app.services import (
    AssetService,
    GroupService,
    KPIService,
    TaskRunService,
)

from worker.celery_app import app as celery_app
from worker.tasks import (
    recompute_calendar_kpis_task,
    recompute_rolling_kpis_task,
)


@pytest.fixture
def celery_config():
    return {
        "broker_url": "redis://localhost:6379/0",
        "result_backend": "redis://localhost:6379/0",
        "task_always_eager": True,
        "task_eager_propagates": True,
    }


@pytest.fixture
def test_assets(db: Session):
    assets = []
    for i in range(3):
        asset = AssetService.create_asset(
            db, name=f"Test Asset {i}", description=f"Description {i}"
        )
        assets.append(asset)
    return assets


@pytest.fixture
def test_groups(db: Session):
    groups = []
    for i in range(2):
        group = GroupService.create_group(
            db, name=f"Test Group {i}", description=f"Description {i}"
        )
        groups.append(group)
    return groups


class TestKPITasks:
    def test_recompute_rolling_kpis_all_assets_with_task_run(
        self, db: Session, test_assets
    ):
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_rolling_kpis_task",
            scope="all_assets",
        )

        result = recompute_rolling_kpis_task(
            task_run_id=task_run.id,
            scope="all",
            target_id=None,
        )

        assert result["status"] == "success"
        assert result["items_processed"] >= len(test_assets)

        updated_task_run = TaskRunService.get_task_run(db, task_run.id)
        assert updated_task_run.status == TaskRunStatus.SUCCESS
        assert updated_task_run.completed_at is not None
        assert updated_task_run.items_processed >= len(test_assets)

    def test_recompute_rolling_kpis_single_asset(
        self, db: Session, test_assets
    ):
        asset = test_assets[0]
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_rolling_kpis_task",
            scope="single_asset",
            asset_id=asset.id,
        )

        result = recompute_rolling_kpis_task(
            task_run_id=task_run.id,
            scope="asset",
            target_id=asset.id,
        )

        assert result["status"] == "success"
        assert result["items_processed"] == 1

        updated_task_run = TaskRunService.get_task_run(db, task_run.id)
        assert updated_task_run.status == TaskRunStatus.SUCCESS
        assert updated_task_run.items_processed == 1

    def test_recompute_calendar_kpis_all_groups_with_task_run(
        self, db: Session, test_groups
    ):
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_calendar_kpis_task",
            scope="all_groups",
        )

        result = recompute_calendar_kpis_task(
            task_run_id=task_run.id,
            scope="all",
            target_id=None,
        )

        assert result["status"] == "success"
        assert result["items_processed"] >= len(test_groups)

        updated_task_run = TaskRunService.get_task_run(db, task_run.id)
        assert updated_task_run.status == TaskRunStatus.SUCCESS
        assert updated_task_run.completed_at is not None
        assert updated_task_run.items_processed >= len(test_groups)

    def test_recompute_calendar_kpis_single_group(
        self, db: Session, test_groups
    ):
        group = test_groups[0]
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_calendar_kpis_task",
            scope="single_group",
            group_id=group.id,
        )

        result = recompute_calendar_kpis_task(
            task_run_id=task_run.id,
            scope="group",
            target_id=group.id,
        )

        assert result["status"] == "success"
        assert result["items_processed"] == 1

        updated_task_run = TaskRunService.get_task_run(db, task_run.id)
        assert updated_task_run.status == TaskRunStatus.SUCCESS
        assert updated_task_run.items_processed == 1

    def test_recompute_rolling_kpis_creates_snapshots(
        self, db: Session, test_assets
    ):
        asset = test_assets[0]
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_rolling_kpis_task",
            asset_id=asset.id,
        )

        result = recompute_rolling_kpis_task(
            task_run_id=task_run.id,
            scope="asset",
            target_id=asset.id,
        )

        assert result["status"] == "success"

        snapshots = (
            db.query(KPISnapshot)
            .filter(KPISnapshot.asset_id == asset.id)
            .all()
        )
        assert len(snapshots) > 0
        assert snapshots[-1].kpi_type == "rolling"

    def test_recompute_calendar_kpis_creates_snapshots(
        self, db: Session, test_groups
    ):
        group = test_groups[0]
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_calendar_kpis_task",
            group_id=group.id,
        )

        result = recompute_calendar_kpis_task(
            task_run_id=task_run.id,
            scope="group",
            target_id=group.id,
        )

        assert result["status"] == "success"

        snapshots = (
            db.query(KPISnapshot)
            .filter(KPISnapshot.group_id == group.id)
            .all()
        )
        assert len(snapshots) > 0
        assert snapshots[-1].kpi_type == "calendar"

    def test_recompute_rolling_kpis_without_task_run_id(
        self, db: Session, test_assets
    ):
        result = recompute_rolling_kpis_task(
            task_run_id=None,
            scope="all",
            target_id=None,
        )

        assert result["status"] == "success"
        assert result["items_processed"] >= len(test_assets)

    def test_recompute_rolling_kpis_error_handling(
        self, db: Session
    ):
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_rolling_kpis_task",
        )

        with mock.patch(
            "worker.tasks.AssetService.list_assets",
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(Exception):
                recompute_rolling_kpis_task(
                    task_run_id=task_run.id,
                    scope="all",
                    target_id=None,
                )

        updated_task_run = TaskRunService.get_task_run(db, task_run.id)
        assert updated_task_run.status == TaskRunStatus.FAILED
        assert "Test error" in updated_task_run.error_message

    def test_recompute_calendar_kpis_error_handling(
        self, db: Session
    ):
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_calendar_kpis_task",
        )

        with mock.patch(
            "worker.tasks.GroupService.list_groups",
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(Exception):
                recompute_calendar_kpis_task(
                    task_run_id=task_run.id,
                    scope="all",
                    target_id=None,
                )

        updated_task_run = TaskRunService.get_task_run(db, task_run.id)
        assert updated_task_run.status == TaskRunStatus.FAILED
        assert "Test error" in updated_task_run.error_message
