import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import UserRole
from app.security import create_access_token
from app.services import UserService


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client(test_db):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db):
    db = TestingSessionLocal()
    try:
        user = UserService.create_user(
            db=db,
            email="test@example.com",
            password="testpassword123",
            full_name="Test User",
            role=UserRole.OPERATOR,
        )
        return user
    finally:
        db.close()


@pytest.fixture
def maintainer_user(test_db):
    db = TestingSessionLocal()
    try:
        user = UserService.create_user(
            db=db,
            email="maintainer@example.com",
            password="maintainerpass123",
            full_name="Maintainer User",
            role=UserRole.MAINTAINER,
        )
        return user
    finally:
        db.close()


def test_login_success(test_client, test_user):
    response = test_client.post(
        "/auth/login",
        params={"email": "test@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(test_client, test_user):
    response = test_client.post(
        "/auth/login",
        params={"email": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_login_user_not_found(test_client):
    response = test_client.post(
        "/auth/login",
        params={"email": "nonexistent@example.com", "password": "password"},
    )
    assert response.status_code == 401


def test_get_me(test_client, test_user):
    db = TestingSessionLocal()
    try:
        token = create_access_token(data={"sub": test_user.id, "role": test_user.role.value})
    finally:
        db.close()

    response = test_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == "test@example.com"
    assert data["role"] == "operator"


def test_me_without_token(test_client):
    response = test_client.get("/auth/me")
    assert response.status_code == 403


def test_me_with_invalid_token(test_client):
    response = test_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


def test_refresh_token(test_client, test_user):
    db = TestingSessionLocal()
    try:
        login_response = test_client.post(
            "/auth/login",
            params={"email": "test@example.com", "password": "testpassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        refresh_response = test_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    finally:
        db.close()


def test_refresh_token_invalid(test_client):
    response = test_client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )
    assert response.status_code == 401


def test_register_as_maintainer(test_client, maintainer_user):
    db = TestingSessionLocal()
    try:
        token = create_access_token(
            data={"sub": maintainer_user.id, "role": maintainer_user.role.value}
        )
    finally:
        db.close()

    response = test_client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "operator"


def test_register_as_non_maintainer(test_client, test_user):
    db = TestingSessionLocal()
    try:
        token = create_access_token(
            data={"sub": test_user.id, "role": test_user.role.value}
        )
    finally:
        db.close()

    response = test_client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_register_duplicate_email(test_client, maintainer_user, test_user):
    db = TestingSessionLocal()
    try:
        token = create_access_token(
            data={"sub": maintainer_user.id, "role": maintainer_user.role.value}
        )
    finally:
        db.close()

    response = test_client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "newpassword123",
            "full_name": "Duplicate User",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_logout(test_client, test_user):
    db = TestingSessionLocal()
    try:
        token = create_access_token(data={"sub": test_user.id, "role": test_user.role.value})
    finally:
        db.close()

    response = test_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
