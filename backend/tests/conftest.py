from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_unit_of_work
from app.auth import API_KEY_HEADER, API_KEY_VALUE
from app.database import Base
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.main import app

TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine) -> sessionmaker[Session]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def override_unit_of_work(session_factory: sessionmaker[Session]) -> Generator[None, None, None]:
    def _get_test_uow() -> Generator[SqlAlchemyUnitOfWork, None, None]:
        with SqlAlchemyUnitOfWork(session_factory=session_factory) as uow:
            yield uow

    app.dependency_overrides[get_unit_of_work] = _get_test_uow
    yield
    app.dependency_overrides.pop(get_unit_of_work, None)


@pytest.fixture()
async def async_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers[API_KEY_HEADER] = API_KEY_VALUE
        yield client


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {API_KEY_HEADER: API_KEY_VALUE}


@pytest.fixture()
def create_asset(db_session: Session) -> Callable[[str, str, str | None], int]:
    from app.models import Asset

    def _create(name: str, group: str, description: str | None = None) -> int:
        asset = Asset(name=name, asset_group=group, description=description)
        db_session.add(asset)
        db_session.commit()
        return asset.id

    return _create
