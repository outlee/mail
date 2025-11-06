from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.repositories import AssetRepository, FailureEventRepository, RuntimeCounterRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None
        self.assets: AssetRepository
        self.runtime_counters: RuntimeCounterRepository
        self.failure_events: FailureEventRepository

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.assets = AssetRepository(self.session)
        self.runtime_counters = RuntimeCounterRepository(self.session)
        self.failure_events = FailureEventRepository(self.session)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        assert self.session is not None
        try:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
        finally:
            self.session.close()

    def __call__(self) -> Generator["SqlAlchemyUnitOfWork", None, None]:
        with self as uow:
            yield uow

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work session is not initialized")
        self.session.rollback()

    def flush(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work session is not initialized")
        self.session.flush()


__all__ = ["SqlAlchemyUnitOfWork"]
