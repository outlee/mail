from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies import get_unit_of_work
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.models import RuntimeCounter
from app.schemas.common import Pagination
from app.schemas.runtime_counters import (
    RuntimeCounterCreate,
    RuntimeCounterListResponse,
    RuntimeCounterRead,
    RuntimeCounterUpdate,
)

router = APIRouter()


@router.get("/", response_model=RuntimeCounterListResponse)
def list_runtime_counters(
    *,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    asset_id: int | None = Query(default=None, gt=0),
    window_start: datetime | None = Query(default=None, alias="start"),
    window_end: datetime | None = Query(default=None, alias="end"),
    include_archived: bool = Query(default=False),
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> RuntimeCounterListResponse:
    if window_start and window_end and window_start > window_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="window_start must be before or equal to window_end",
        )

    items, total, delta_sum = uow.runtime_counters.list(
        limit=limit,
        offset=offset,
        asset_id=asset_id,
        window_start=window_start,
        window_end=window_end,
        include_archived=include_archived,
    )
    return RuntimeCounterListResponse(
        items=items,
        pagination=Pagination(total=total, limit=limit, offset=offset),
        delta_hours_total=delta_sum,
    )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=RuntimeCounterRead)
def create_runtime_counter(
    payload: RuntimeCounterCreate,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> RuntimeCounterRead:
    asset = uow.assets.get(payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    runtime_counter = RuntimeCounter(
        asset_id=payload.asset_id,
        recorded_at=payload.recorded_at,
        total_hours=payload.total_hours,
        attributes=payload.metadata,
    )
    try:
        uow.runtime_counters.add(runtime_counter)
        uow.flush()
    except ValueError as exc:
        uow.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RuntimeCounterRead.model_validate(runtime_counter)


@router.get("/{runtime_counter_id}", response_model=RuntimeCounterRead)
def get_runtime_counter(
    runtime_counter_id: int,
    include_archived: bool = Query(default=False),
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> RuntimeCounterRead:
    runtime_counter = uow.runtime_counters.get(runtime_counter_id, include_archived=include_archived)
    if runtime_counter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Runtime counter not found")
    return RuntimeCounterRead.model_validate(runtime_counter)


@router.patch("/{runtime_counter_id}", response_model=RuntimeCounterRead)
def update_runtime_counter(
    runtime_counter_id: int,
    payload: RuntimeCounterUpdate,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> RuntimeCounterRead:
    runtime_counter = uow.runtime_counters.get(runtime_counter_id)
    if runtime_counter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Runtime counter not found")

    update_data = payload.model_dump(exclude_unset=True)
    update_kwargs: dict[str, object] = {}
    if "total_hours" in update_data:
        update_kwargs["total_hours"] = update_data["total_hours"]
    if "recorded_at" in update_data:
        update_kwargs["recorded_at"] = update_data["recorded_at"]
    if "metadata" in update_data:
        update_kwargs["attributes"] = update_data["metadata"]

    try:
        uow.runtime_counters.update(runtime_counter, **update_kwargs)
        uow.flush()
    except ValueError as exc:
        uow.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RuntimeCounterRead.model_validate(runtime_counter)


@router.delete("/{runtime_counter_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_runtime_counter(
    runtime_counter_id: int,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> Response:
    runtime_counter = uow.runtime_counters.get(runtime_counter_id)
    if runtime_counter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Runtime counter not found")

    try:
        uow.runtime_counters.archive(runtime_counter)
        uow.flush()
    except ValueError as exc:
        uow.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
