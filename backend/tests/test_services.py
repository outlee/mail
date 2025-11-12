import pytest
from sqlalchemy.orm import Session

from app.models.asset import Asset, Group
from app.models.auth import User, UserRole
from app.models.kpi import KPISnapshot
from app.models.monitoring import TaskRun, TaskRunStatus
from app.services import AssetService, GroupService, KPIService, TaskRunService, UserService


class TestUserService:
    def test_create_user(self, db: Session):
        user = UserService.create_user(
            db=db,
            email="newuser@example.com",
            password="password123",
            full_name="New User",
            role=UserRole.OPERATOR,
        )
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.role == UserRole.OPERATOR
        assert user.is_active is True

    def test_get_user_by_email(self, db: Session, sample_user: User):
        user = UserService.get_user_by_email(db, sample_user.email)
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email

    def test_get_user_by_email_not_found(self, db: Session):
        user = UserService.get_user_by_email(db, "nonexistent@example.com")
        assert user is None

    def test_get_user_by_id(self, db: Session, sample_user: User):
        user = UserService.get_user_by_id(db, sample_user.id)
        assert user is not None
        assert user.id == sample_user.id

    def test_get_user_by_id_not_found(self, db: Session):
        user = UserService.get_user_by_id(db, "nonexistent-id")
        assert user is None

    def test_authenticate_user_success(self, db: Session, sample_user: User):
        user = UserService.authenticate_user(db, "test@example.com", "password123")
        assert user is not None
        assert user.id == sample_user.id

    def test_authenticate_user_wrong_password(self, db: Session, sample_user: User):
        user = UserService.authenticate_user(db, "test@example.com", "wrongpassword")
        assert user is None

    def test_authenticate_user_not_found(self, db: Session):
        user = UserService.authenticate_user(db, "nonexistent@example.com", "password123")
        assert user is None


class TestAssetService:
    def test_create_asset(self, db: Session):
        asset = AssetService.create_asset(
            db=db, name="New Asset", description="New asset description"
        )
        assert asset.id is not None
        assert asset.name == "New Asset"
        assert asset.description == "New asset description"

    def test_create_asset_without_description(self, db: Session):
        asset = AssetService.create_asset(db=db, name="Asset Without Description")
        assert asset.id is not None
        assert asset.name == "Asset Without Description"
        assert asset.description is None

    def test_get_asset_by_id(self, db: Session, sample_asset: Asset):
        asset = AssetService.get_asset_by_id(db, sample_asset.id)
        assert asset is not None
        assert asset.id == sample_asset.id
        assert asset.name == sample_asset.name

    def test_get_asset_by_id_not_found(self, db: Session):
        asset = AssetService.get_asset_by_id(db, "nonexistent-id")
        assert asset is None

    def test_list_assets(self, db: Session, sample_asset: Asset):
        assets = AssetService.list_assets(db)
        assert len(assets) >= 1
        assert any(a.id == sample_asset.id for a in assets)

    def test_list_assets_with_pagination(self, db: Session):
        for i in range(5):
            AssetService.create_asset(db=db, name=f"Asset {i}")

        assets_page_1 = AssetService.list_assets(db, skip=0, limit=2)
        assert len(assets_page_1) == 2

        assets_page_2 = AssetService.list_assets(db, skip=2, limit=2)
        assert len(assets_page_2) == 2

        assert assets_page_1[0].id != assets_page_2[0].id


class TestGroupService:
    def test_create_group(self, db: Session):
        group = GroupService.create_group(
            db=db, name="New Group", description="New group description"
        )
        assert group.id is not None
        assert group.name == "New Group"
        assert group.description == "New group description"

    def test_create_group_without_description(self, db: Session):
        group = GroupService.create_group(db=db, name="Group Without Description")
        assert group.id is not None
        assert group.name == "Group Without Description"
        assert group.description is None

    def test_get_group_by_id(self, db: Session, sample_group: Group):
        group = GroupService.get_group_by_id(db, sample_group.id)
        assert group is not None
        assert group.id == sample_group.id
        assert group.name == sample_group.name

    def test_get_group_by_id_not_found(self, db: Session):
        group = GroupService.get_group_by_id(db, "nonexistent-id")
        assert group is None

    def test_list_groups(self, db: Session, sample_group: Group):
        groups = GroupService.list_groups(db)
        assert len(groups) >= 1
        assert any(g.id == sample_group.id for g in groups)

    def test_list_groups_with_pagination(self, db: Session):
        for i in range(5):
            GroupService.create_group(db=db, name=f"Group {i}")

        groups_page_1 = GroupService.list_groups(db, skip=0, limit=2)
        assert len(groups_page_1) == 2

        groups_page_2 = GroupService.list_groups(db, skip=2, limit=2)
        assert len(groups_page_2) == 2

        assert groups_page_1[0].id != groups_page_2[0].id


class TestKPIService:
    def test_recompute_asset_kpis(self, db: Session, sample_asset: Asset):
        result = KPIService.recompute_asset_kpis(
            db=db, asset_id=sample_asset.id, kpi_type="rolling"
        )
        assert result is True

        snapshots = db.query(KPISnapshot).filter_by(asset_id=sample_asset.id).all()
        assert len(snapshots) >= 1

    def test_recompute_asset_kpis_not_found(self, db: Session):
        result = KPIService.recompute_asset_kpis(
            db=db, asset_id="nonexistent-id", kpi_type="rolling"
        )
        assert result is False

    def test_recompute_group_kpis(self, db: Session, sample_group: Group):
        result = KPIService.recompute_group_kpis(
            db=db, group_id=sample_group.id, kpi_type="calendar"
        )
        assert result is True

        snapshots = db.query(KPISnapshot).filter_by(group_id=sample_group.id).all()
        assert len(snapshots) >= 1

    def test_recompute_group_kpis_not_found(self, db: Session):
        result = KPIService.recompute_group_kpis(
            db=db, group_id="nonexistent-id", kpi_type="calendar"
        )
        assert result is False


class TestTaskRunService:
    def test_create_task_run(self, db: Session):
        task_run = TaskRunService.create_task_run(
            db=db,
            task_name="test_task",
            scope="all_assets",
            task_id="test-task-id",
        )
        assert task_run.id is not None
        assert task_run.task_name == "test_task"
        assert task_run.scope == "all_assets"
        assert task_run.status == TaskRunStatus.PENDING

    def test_get_task_run(self, db: Session, sample_task_run: TaskRun):
        task_run = TaskRunService.get_task_run(db, sample_task_run.id)
        assert task_run is not None
        assert task_run.id == sample_task_run.id

    def test_get_task_run_not_found(self, db: Session):
        task_run = TaskRunService.get_task_run(db, "nonexistent-id")
        assert task_run is None

    def test_update_task_run(self, db: Session, sample_task_run: TaskRun):
        updated = TaskRunService.update_task_run(
            db=db,
            task_run_id=sample_task_run.id,
            status=TaskRunStatus.SUCCESS,
            items_processed=10,
        )
        assert updated is not None
        assert updated.status == TaskRunStatus.SUCCESS
        assert updated.items_processed == "10"

    def test_start_task_run(self, db: Session, sample_task_run: TaskRun):
        started = TaskRunService.start_task_run(db, sample_task_run.id)
        assert started is not None
        assert started.status == TaskRunStatus.RUNNING
        assert started.started_at is not None

    def test_list_task_runs(self, db: Session, sample_task_run: TaskRun):
        task_runs = TaskRunService.list_task_runs(db)
        assert len(task_runs) >= 1
        assert any(tr.id == sample_task_run.id for tr in task_runs)

    def test_list_task_runs_with_filter(self, db: Session):
        TaskRunService.create_task_run(db=db, task_name="task1", scope="test1")
        TaskRunService.create_task_run(db=db, task_name="task2", scope="test2")

        filtered_runs = TaskRunService.list_task_runs(db, task_name="task1")
        assert all(tr.task_name == "task1" for tr in filtered_runs)
