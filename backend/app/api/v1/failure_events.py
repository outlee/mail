from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies import get_unit_of_work
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.models import FailureEvent
from app.schemas.common import Pagination
from app.schemas.failure_events import (
    FailureEventCreate,
    FailureEventListResponse,
    FailureEventRead,
    FailureEventUpdate,
)

router = APIRouter()


@router.get("/", response_model=FailureEventListResponse)
def list_failure_events(
    *,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    asset_id: int | None = Query(default=None, gt=0),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    include_archived: bool = Query(default=False),
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> FailureEventListResponse:
    if start and end and start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start must be before or equal to end",
        )

    items, total = uow.failure_events.list(
        limit=limit,
        offset=offset,
        asset_id=asset_id,
        start=start,
        end=end,
        include_archived=include_archived,
    )
    return FailureEventListResponse(
        items=items,
        pagination=Pagination(total=total, limit=limit, offset=offset),
    )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=FailureEventRead)
def create_failure_event(
    payload: FailureEventCreate,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> FailureEventRead:
    asset = uow.assets.get(payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    failure_event = FailureEvent(
        asset_id=payload.asset_id,
        occurred_at=payload.occurred_at,
        resolved_at=payload.resolved_at,
        description=payload.description,
        attributes=payload.metadata,
    )
    try:
        uow.failure_events.add(failure_event)
        uow.flush()
    except ValueError as exc:
        uow.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FailureEventRead.model_validate(failure_event)


@router.get("/{failure_event_id}", response_model=FailureEventRead)
def get_failure_event(
    failure_event_id: int,
    include_archived: bool = Query(default=False),
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> FailureEventRead:
    failure_event = uow.failure_events.get(failure_event_id, include_archived=include_archived)
    if failure_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failure event not found")
    return FailureEventRead.model_validate(failure_event)


@router.patch("/{failure_event_id}", response_model=FailureEventRead)
def update_failure_event(
    failure_event_id: int,
    payload: FailureEventUpdate,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> FailureEventRead:
    failure_event = uow.failure_events.get(failure_event_id)
    if failure_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failure event not found")

    update_data = payload.model_dump(exclude_unset=True)
    update_kwargs: dict[str, object] = {}
    if "occurred_at" in update_data:
        update_kwargs["occurred_at"] = update_data["occurred_at"]
    if "resolved_at" in update_data:
        update_kwargs["resolved_at"] = update_data["resolved_at"]
    if "description" in update_data:
        update_kwargs["description"] = update_data["description"]
    if "metadata" in update_data:
        update_kwargs["attributes"] = update_data["metadata"]

    try:
        uow.failure_events.update(failure_event, **update_kwargs)
        uow.flush()
    except ValueError as exc:
        uow.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FailureEventRead.model_validate(failure_event)


@router.delete("/{failure_event_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_failure_event(
    failure_event_id: int,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> Response:
    failure_event = uow.failure_events.get(failure_event_id)
    if failure_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failure event not found")

    uow.failure_events.archive(failure_event)
    uow.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
