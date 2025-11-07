import uuid
from datetime import datetime, timedelta
from unittest import mock

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Asset, Group, KPISnapshot, TaskRun, TaskRunStatus
from app.services import (
    AssetService,
    GroupService,
    KPIService,
    TaskRunService,
)


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
    for i in range(3):
        group = GroupService.create_group(
            db, name=f"Test Group {i}", description=f"Description {i}"
        )
        groups.append(group)
    return groups


class TestKPIService:
    def test_recompute_asset_kpis_success(self, db: Session, test_assets):
        asset = test_assets[0]

        result = KPIService.recompute_asset_kpis(
            db, asset.id, kpi_type="rolling"
        )

        assert result is True
        snapshots = (
            db.query(KPISnapshot)
            .filter(KPISnapshot.asset_id == asset.id)
            .all()
        )
        assert len(snapshots) > 0
        assert snapshots[0].kpi_type == "rolling"
        assert snapshots[0].value == 95.0

    def test_recompute_group_kpis_success(self, db: Session, test_groups):
        group = test_groups[0]

        result = KPIService.recompute_group_kpis(
            db, group.id, kpi_type="calendar"
        )

        assert result is True
        snapshots = (
            db.query(KPISnapshot)
            .filter(KPISnapshot.group_id == group.id)
            .all()
        )
        assert len(snapshots) > 0
        assert snapshots[0].kpi_type == "calendar"
        assert snapshots[0].value == 92.0

    def test_recompute_asset_kpis_nonexistent_asset(self, db: Session):
        nonexistent_id = str(uuid.uuid4())

        result = KPIService.recompute_asset_kpis(db, nonexistent_id)

        assert result is False

    def test_recompute_group_kpis_nonexistent_group(self, db: Session):
        nonexistent_id = str(uuid.uuid4())

        result = KPIService.recompute_group_kpis(db, nonexistent_id)

        assert result is False

    def test_concurrent_lock_handling(self, db: Session, test_assets):
        asset = test_assets[0]
        lock_id = KPIService._generate_lock_id("kpi", asset.id)

        acquired1 = KPIService.acquire_lock(db, lock_id)
        assert acquired1 is True

        KPIService.release_lock(db, lock_id)


class TestTaskRunService:
    def test_create_task_run(self, db: Session):
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_kpis",
            scope="all_assets",
        )

        assert task_run.id is not None
        assert task_run.task_name == "recompute_kpis"
        assert task_run.scope == "all_assets"
        assert task_run.status == TaskRunStatus.PENDING

    def test_start_task_run(self, db: Session):
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_kpis",
        )

        started_run = TaskRunService.start_task_run(db, task_run.id)

        assert started_run.status == TaskRunStatus.RUNNING
        assert started_run.started_at is not None

    def test_update_task_run_success(self, db: Session):
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_kpis",
        )

        updated_run = TaskRunService.update_task_run(
            db=db,
            task_run_id=task_run.id,
            status=TaskRunStatus.SUCCESS,
            completed_at=datetime.utcnow(),
            items_processed=5,
        )

        assert updated_run.status == TaskRunStatus.SUCCESS
        assert updated_run.completed_at is not None
        assert updated_run.items_processed == 5

    def test_update_task_run_failed(self, db: Session):
        task_run = TaskRunService.create_task_run(
            db,
            task_name="recompute_kpis",
        )

        updated_run = TaskRunService.update_task_run(
            db=db,
            task_run_id=task_run.id,
            status=TaskRunStatus.FAILED,
            error_message="Test error",
            completed_at=datetime.utcnow(),
        )

        assert updated_run.status == TaskRunStatus.FAILED
        assert updated_run.error_message == "Test error"

    def test_list_task_runs(self, db: Session):
        for i in range(3):
            TaskRunService.create_task_run(
                db,
                task_name="recompute_kpis",
                scope=f"scope_{i}",
            )

        runs = TaskRunService.list_task_runs(db, limit=10)

        assert len(runs) >= 3

    def test_list_task_runs_by_name(self, db: Session):
        for i in range(2):
            TaskRunService.create_task_run(
                db,
                task_name="recompute_kpis",
            )

        for i in range(2):
            TaskRunService.create_task_run(
                db,
                task_name="other_task",
            )

        runs = TaskRunService.list_task_runs(
            db, task_name="recompute_kpis", limit=10
        )

        assert len(runs) >= 2
        assert all(r.task_name == "recompute_kpis" for r in runs)

    def test_get_task_run(self, db: Session):
        created_run = TaskRunService.create_task_run(
            db,
            task_name="test_task",
        )

        fetched_run = TaskRunService.get_task_run(db, created_run.id)

        assert fetched_run is not None
        assert fetched_run.id == created_run.id
        assert fetched_run.task_name == "test_task"


class TestAssetAndGroupServices:
    def test_create_and_get_asset(self, db: Session):
        asset = AssetService.create_asset(db, "Test Asset", "Test Description")

        fetched = AssetService.get_asset_by_id(db, asset.id)

        assert fetched is not None
        assert fetched.name == "Test Asset"
        assert fetched.description == "Test Description"

    def test_list_assets(self, db: Session, test_assets):
        assets = AssetService.list_assets(db, limit=10)

        assert len(assets) >= len(test_assets)

    def test_create_and_get_group(self, db: Session):
        group = GroupService.create_group(db, "Test Group", "Test Description")

        fetched = GroupService.get_group_by_id(db, group.id)

        assert fetched is not None
        assert fetched.name == "Test Group"
        assert fetched.description == "Test Description"

    def test_list_groups(self, db: Session, test_groups):
        groups = GroupService.list_groups(db, limit=10)

        assert len(groups) >= len(test_groups)
