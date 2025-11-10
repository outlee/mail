import shutil
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings as get_app_settings
from app.database import Base, get_db
from app.main import app
from app.models import Asset, CSVImportStatus, FailureEvent, RuntimeCounter, UserRole
from app.security import create_access_token
from app.services import AssetService, UserService
from worker.config import get_settings as get_worker_settings
from worker.worker import tasks as worker_tasks

TEST_DATABASE_URL = "sqlite:///./test_csv_imports.db"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database(tmp_path):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

    storage_dir = tmp_path / "csv_storage"
    if storage_dir.exists():
        shutil.rmtree(storage_dir)


@pytest.fixture
def test_client(tmp_path):
    storage_dir = tmp_path / "csv_storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    app_settings = get_app_settings()
    worker_settings = get_worker_settings()

    original_app_storage = app_settings.csv_import_storage_path
    original_worker_storage = worker_settings.csv_import_storage_path
    app_settings.csv_import_storage_path = str(storage_dir)
    worker_settings.csv_import_storage_path = str(storage_dir)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    original_session_local = worker_tasks.SessionLocal
    original_worker_task_storage = worker_tasks.settings.csv_import_storage_path
    original_worker_task_error_sample_size = (
        worker_tasks.settings.csv_import_error_sample_size
    )

    worker_tasks.SessionLocal = TestingSessionLocal
    worker_tasks.settings.csv_import_storage_path = str(storage_dir)
    worker_tasks.settings.csv_import_error_sample_size = 5

    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        worker_tasks.SessionLocal = original_session_local
        worker_tasks.settings.csv_import_storage_path = original_worker_task_storage
        worker_tasks.settings.csv_import_error_sample_size = (
            original_worker_task_error_sample_size
        )
        app_settings.csv_import_storage_path = original_app_storage
        worker_settings.csv_import_storage_path = original_worker_storage


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_headers(db_session):
    user = UserService.create_user(
        db=db_session,
        email="maintainer@example.com",
        password="strong-password",
        full_name="Maintainer",
        role=UserRole.MAINTAINER,
    )
    token = create_access_token(data={"sub": user.id, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_send_task():
    with patch("app.routes.celery_app.send_task") as mock_task:
        mock_task.return_value = MagicMock(id="mock-task-id")
        yield mock_task


def test_import_requires_idempotency_key(test_client, auth_headers, mock_send_task):
    response = test_client.post(
        "/api/v1/imports/assets",
        files={
            "file": (
                "assets.csv",
                b"external_id,name\na-1,Asset 1\n",
                "text/csv",
            )
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "X-Idempotency-Key" in response.json()["detail"]
    assert mock_send_task.call_count == 0


def test_import_rejects_unsupported_content_type(test_client, auth_headers, mock_send_task):
    headers = {**auth_headers, "X-Idempotency-Key": "ct-test"}

    response = test_client.post(
        "/api/v1/imports/assets",
        files={"file": ("assets.txt", b"hello", "text/plain")},
        headers=headers,
    )

    assert response.status_code == 415
    assert "Unsupported content type" in response.json()["detail"]
    assert mock_send_task.call_count == 0


def test_asset_import_success_flow(test_client, auth_headers, mock_send_task, db_session):
    headers = {**auth_headers, "X-Idempotency-Key": "asset-success"}
    payload = (
        "external_id,name,description\n"
        "asset-1,Main Asset,Primary\n"
        "asset-2,Backup Asset,Secondary\n"
    ).encode("utf-8")

    response = test_client.post(
        "/api/v1/imports/assets",
        files={"file": ("assets.csv", payload, "text/csv")},
        headers=headers,
    )

    assert response.status_code == 202
    data = response.json()
    job_id = data["id"]
    assert data["status"] == CSVImportStatus.PENDING.value
    assert mock_send_task.call_count == 1

    worker_tasks.process_csv_import_task.run(job_id)

    status_response = test_client.get(
        f"/api/v1/imports/{job_id}",
        headers=auth_headers,
    )
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == CSVImportStatus.COMPLETED.value
    assert status_data["processed_rows"] == 2
    assert status_data["error_rows"] == 0

    assets = db_session.query(Asset).order_by(Asset.external_id).all()
    assert len(assets) == 2
    assert assets[0].name == "Main Asset"
    assert assets[1].description == "Secondary"


def test_import_idempotency_returns_existing_job(
    test_client, auth_headers, mock_send_task
):
    headers = {**auth_headers, "X-Idempotency-Key": "duplicate-key"}
    payload = b"external_id,name\na-1,Asset 1\n"

    first_response = test_client.post(
        "/api/v1/imports/assets",
        files={"file": ("assets.csv", payload, "text/csv")},
        headers=headers,
    )
    assert first_response.status_code == 202
    first_job = first_response.json()

    second_response = test_client.post(
        "/api/v1/imports/assets",
        files={"file": ("assets.csv", payload, "text/csv")},
        headers=headers,
    )
    assert second_response.status_code == 202
    second_job = second_response.json()

    assert first_job["id"] == second_job["id"]
    assert mock_send_task.call_count == 1


def test_runtime_import_partial_failure(
    test_client, auth_headers, mock_send_task, db_session
):
    valid_asset = AssetService.create_asset(
        db=db_session,
        name="Valid Asset",
        description="",
        external_id="asset-existing",
    )
    db_session.expunge(valid_asset)

    headers = {**auth_headers, "X-Idempotency-Key": "runtime-partial"}
    csv_payload = (
        "asset_external_id,counter_name,value,recorded_at\n"
        "asset-existing,uptime_hours,12.5,2023-10-01T00:00:00Z\n"
        "asset-missing,uptime_hours,8.1,2023-10-01T01:00:00Z\n"
    ).encode("utf-8")

    response = test_client.post(
        "/api/v1/imports/runtime",
        files={"file": ("runtime.csv", csv_payload, "text/csv")},
        headers=headers,
    )
    assert response.status_code == 202
    job_id = response.json()["id"]

    worker_tasks.process_csv_import_task.run(job_id)

    status_response = test_client.get(
        f"/api/v1/imports/{job_id}",
        headers=auth_headers,
    )
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["status"] == CSVImportStatus.COMPLETED.value
    assert data["processed_rows"] == 1
    assert data["error_rows"] == 1
    assert data["skipped_rows"] == 1
    assert len(data["error_sample"]) == 1
    assert "does not exist" in data["error_sample"][0]["error"]

    db_session.expire_all()
    runtime_counters = db_session.query(RuntimeCounter).all()
    assert len(runtime_counters) == 1
    assert runtime_counters[0].asset_id == valid_asset.id
    assert runtime_counters[0].counter_name == "uptime_hours"
    assert runtime_counters[0].value == 12.5
    assert mock_send_task.call_count == 1


def test_failure_import_success(
    test_client, auth_headers, mock_send_task, db_session
):
    asset = AssetService.create_asset(
        db=db_session,
        name="Failure Asset",
        description="",
        external_id="asset-failure",
    )
    db_session.expunge(asset)

    headers = {**auth_headers, "X-Idempotency-Key": "failure-success"}
    csv_payload = (
        "asset_external_id,failure_code,occurred_at,description,resolved_at\n"
        "asset-failure,FAIL-001,2023-10-01T00:00:00Z,Motor fault,2023-10-02T00:00:00Z\n"
    ).encode("utf-8")

    response = test_client.post(
        "/api/v1/imports/failures",
        files={"file": ("failures.csv", csv_payload, "text/csv")},
        headers=headers,
    )
    assert response.status_code == 202
    job_id = response.json()["id"]

    worker_tasks.process_csv_import_task.run(job_id)

    status_response = test_client.get(
        f"/api/v1/imports/{job_id}",
        headers=auth_headers,
    )
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["status"] == CSVImportStatus.COMPLETED.value
    assert data["processed_rows"] == 1
    assert data["error_rows"] == 0

    db_session.expire_all()
    failures = db_session.query(FailureEvent).all()
    assert len(failures) == 1
    assert failures[0].failure_code == "FAIL-001"
    assert failures[0].description == "Motor fault"
    assert failures[0].resolved_at is not None
    assert mock_send_task.call_count == 1
