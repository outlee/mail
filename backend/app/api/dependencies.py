from __future__ import annotations

from collections.abc import Generator

from app.database import SessionLocal
from app.db.unit_of_work import SqlAlchemyUnitOfWork


def get_unit_of_work() -> Generator[SqlAlchemyUnitOfWork, None, None]:
    with SqlAlchemyUnitOfWork(session_factory=SessionLocal) as uow:
        yield uow
