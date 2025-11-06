from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Asset, FailureEvent, RuntimeCounter

UNSET = object()


class AssetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, asset: Asset) -> Asset:
        self.session.add(asset)
        return asset

    def get(self, asset_id: int, *, include_archived: bool = False) -> Asset | None:
        asset = self.session.get(Asset, asset_id)
        if asset is None:
            return None
        if not include_archived and asset.is_archived:
            return None
        return asset

    def list(
        self,
        *,
        limit: int,
        offset: int,
        asset_group: str | None,
        include_archived: bool,
    ) -> tuple[list[Asset], int]:
        filters: list[Any] = []
        if not include_archived:
            filters.append(Asset.is_archived.is_(False))
        if asset_group:
            filters.append(Asset.asset_group == asset_group)

        stmt = select(Asset).where(*filters).order_by(Asset.name).offset(offset).limit(limit)
        results = self.session.execute(stmt).scalars().all()

        count_stmt = select(func.count()).select_from(Asset).where(*filters)
        total = self.session.scalar(count_stmt) or 0
        return results, int(total)

    def archive(self, asset: Asset) -> Asset:
        asset.is_archived = True
        asset.archived_at = datetime.now(timezone.utc)
        return asset


class RuntimeCounterRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, runtime_counter: RuntimeCounter) -> RuntimeCounter:
        runtime_counter.delta_hours = self._calculate_delta_for_new(runtime_counter)
        self.session.add(runtime_counter)
        self.session.flush()
        self._sync_next_delta(runtime_counter)
        return runtime_counter

    def get(
        self, runtime_counter_id: int, *, include_archived: bool = False
    ) -> RuntimeCounter | None:
        runtime_counter = self.session.get(RuntimeCounter, runtime_counter_id)
        if runtime_counter is None:
            return None
        if not include_archived and runtime_counter.is_archived:
            return None
        return runtime_counter

    def list(
        self,
        *,
        limit: int,
        offset: int,
        asset_id: int | None,
        window_start: datetime | None,
        window_end: datetime | None,
        include_archived: bool,
    ) -> tuple[list[RuntimeCounter], int, float]:
        filters: list[Any] = []
        if not include_archived:
            filters.append(RuntimeCounter.is_archived.is_(False))
        if asset_id is not None:
            filters.append(RuntimeCounter.asset_id == asset_id)
        if window_start is not None:
            filters.append(RuntimeCounter.recorded_at >= window_start)
        if window_end is not None:
            filters.append(RuntimeCounter.recorded_at <= window_end)

        stmt = (
            select(RuntimeCounter)
            .where(*filters)
            .order_by(RuntimeCounter.recorded_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = self.session.execute(stmt).scalars().all()

        count_stmt = select(func.count()).select_from(RuntimeCounter).where(*filters)
        total = int(self.session.scalar(count_stmt) or 0)

        delta_stmt = select(func.sum(RuntimeCounter.delta_hours)).where(*filters)
        delta_sum = float(self.session.scalar(delta_stmt) or 0.0)
        return items, total, delta_sum

    def update(
        self,
        runtime_counter: RuntimeCounter,
        *,
        total_hours: float | None = None,
        recorded_at: datetime | None = None,
        attributes: dict[str, Any] | None | object = UNSET,
    ) -> RuntimeCounter:
        if total_hours is not None:
            runtime_counter.total_hours = total_hours
        if recorded_at is not None:
            runtime_counter.recorded_at = recorded_at
        if attributes is not UNSET:
            runtime_counter.attributes = attributes

        self.session.flush()
        runtime_counter.delta_hours = self._calculate_delta(runtime_counter)
        self._sync_next_delta(runtime_counter)
        return runtime_counter

    def archive(self, runtime_counter: RuntimeCounter) -> RuntimeCounter:
        runtime_counter.is_archived = True
        runtime_counter.archived_at = datetime.now(timezone.utc)
        self.session.flush()
        self._sync_next_delta(runtime_counter)
        return runtime_counter

    def _calculate_delta_for_new(self, runtime_counter: RuntimeCounter) -> float:
        previous = self._get_previous_runtime_counter(
            asset_id=runtime_counter.asset_id,
            reference_time=runtime_counter.recorded_at,
            exclude_id=None,
        )
        if previous is None:
            if runtime_counter.total_hours < 0:
                raise ValueError("total_hours cannot be negative")
            return runtime_counter.total_hours

        if runtime_counter.total_hours < previous.total_hours:
            raise ValueError("total_hours cannot decrease from the previous entry")
        return runtime_counter.total_hours - previous.total_hours

    def _calculate_delta(self, runtime_counter: RuntimeCounter) -> float:
        previous = self._get_previous_runtime_counter(
            asset_id=runtime_counter.asset_id,
            reference_time=runtime_counter.recorded_at,
            exclude_id=runtime_counter.id,
        )
        if previous is None:
            if runtime_counter.total_hours < 0:
                raise ValueError("total_hours cannot be negative")
            return runtime_counter.total_hours

        if runtime_counter.total_hours < previous.total_hours:
            raise ValueError("total_hours cannot decrease from the previous entry")
        return runtime_counter.total_hours - previous.total_hours

    def _sync_next_delta(self, runtime_counter: RuntimeCounter) -> None:
        next_entry = self._get_next_runtime_counter(
            asset_id=runtime_counter.asset_id,
            reference_time=runtime_counter.recorded_at,
            exclude_id=runtime_counter.id,
        )
        if next_entry is None:
            return

        previous = self._get_previous_runtime_counter(
            asset_id=next_entry.asset_id,
            reference_time=next_entry.recorded_at,
            exclude_id=next_entry.id,
        )
        if previous is None:
            if next_entry.total_hours < 0:
                raise ValueError("total_hours cannot be negative")
            next_entry.delta_hours = next_entry.total_hours
            return

        if next_entry.total_hours < previous.total_hours:
            raise ValueError("next runtime counter total_hours cannot be less than previous total_hours")
        next_entry.delta_hours = next_entry.total_hours - previous.total_hours

    def _get_previous_runtime_counter(
        self,
        *,
        asset_id: int,
        reference_time: datetime,
        exclude_id: int | None,
    ) -> RuntimeCounter | None:
        stmt: Select[tuple[RuntimeCounter]] = (
            select(RuntimeCounter)
            .where(RuntimeCounter.asset_id == asset_id)
            .where(RuntimeCounter.is_archived.is_(False))
            .where(RuntimeCounter.recorded_at <= reference_time)
            .order_by(RuntimeCounter.recorded_at.desc(), RuntimeCounter.id.desc())
            .limit(1)
        )
        if exclude_id is not None:
            stmt = stmt.where(RuntimeCounter.id != exclude_id)

        return self.session.execute(stmt).scalar_one_or_none()

    def _get_next_runtime_counter(
        self,
        *,
        asset_id: int,
        reference_time: datetime,
        exclude_id: int | None,
    ) -> RuntimeCounter | None:
        stmt: Select[tuple[RuntimeCounter]] = (
            select(RuntimeCounter)
            .where(RuntimeCounter.asset_id == asset_id)
            .where(RuntimeCounter.is_archived.is_(False))
            .where(RuntimeCounter.recorded_at > reference_time)
            .order_by(RuntimeCounter.recorded_at.asc(), RuntimeCounter.id.asc())
            .limit(1)
        )
        if exclude_id is not None:
            stmt = stmt.where(RuntimeCounter.id != exclude_id)

        return self.session.execute(stmt).scalar_one_or_none()


class FailureEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, failure_event: FailureEvent) -> FailureEvent:
        failure_event.downtime_minutes = self._calculate_downtime(
            occurred=failure_event.occurred_at,
            resolved=failure_event.resolved_at,
        )
        self.session.add(failure_event)
        return failure_event

    def get(
        self, failure_event_id: int, *, include_archived: bool = False
    ) -> FailureEvent | None:
        failure_event = self.session.get(FailureEvent, failure_event_id)
        if failure_event is None:
            return None
        if not include_archived and failure_event.is_archived:
            return None
        return failure_event

    def list(
        self,
        *,
        limit: int,
        offset: int,
        asset_id: int | None,
        start: datetime | None,
        end: datetime | None,
        include_archived: bool,
    ) -> tuple[list[FailureEvent], int]:
        filters: list[Any] = []
        if not include_archived:
            filters.append(FailureEvent.is_archived.is_(False))
        if asset_id is not None:
            filters.append(FailureEvent.asset_id == asset_id)
        if start is not None:
            filters.append(FailureEvent.occurred_at >= start)
        if end is not None:
            filters.append(FailureEvent.occurred_at <= end)

        stmt = (
            select(FailureEvent)
            .where(*filters)
            .order_by(FailureEvent.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = self.session.execute(stmt).scalars().all()

        count_stmt = select(func.count()).select_from(FailureEvent).where(*filters)
        total = int(self.session.scalar(count_stmt) or 0)
        return items, total

    def update(
        self,
        failure_event: FailureEvent,
        *,
        occurred_at: datetime | None = None,
        resolved_at: datetime | None | object = UNSET,
        description: str | None | object = UNSET,
        attributes: dict[str, Any] | None | object = UNSET,
    ) -> FailureEvent:
        if occurred_at is not None:
            failure_event.occurred_at = occurred_at
        if resolved_at is not UNSET:
            failure_event.resolved_at = resolved_at
        if description is not UNSET:
            failure_event.description = description
        if attributes is not UNSET:
            failure_event.attributes = attributes

        failure_event.downtime_minutes = self._calculate_downtime(
            occurred=failure_event.occurred_at,
            resolved=failure_event.resolved_at,
        )
        return failure_event

    def archive(self, failure_event: FailureEvent) -> FailureEvent:
        failure_event.is_archived = True
        failure_event.archived_at = datetime.now(timezone.utc)
        return failure_event

    @staticmethod
    def _calculate_downtime(*, occurred: datetime, resolved: datetime | None) -> int | None:
        if resolved is None:
            return None
        if resolved < occurred:
            raise ValueError("resolved_at cannot precede occurred_at")
        delta = resolved - occurred
        minutes = int(delta.total_seconds() // 60)
        return max(minutes, 0)
