from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_unit_of_work
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.models import Asset
from app.schemas.assets import AssetCreate, AssetListResponse, AssetRead, AssetUpdate
from app.schemas.common import Pagination

router = APIRouter()


@router.get("/", response_model=AssetListResponse)
def list_assets(
    *,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    asset_group: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> AssetListResponse:
    items, total = uow.assets.list(
        limit=limit,
        offset=offset,
        asset_group=asset_group,
        include_archived=include_archived,
    )
    return AssetListResponse(
        items=items,
        pagination=Pagination(total=total, limit=limit, offset=offset),
    )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AssetRead)
def create_asset(
    payload: AssetCreate,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> AssetRead:
    asset = Asset(
        name=payload.name,
        asset_group=payload.asset_group,
        description=payload.description,
        attributes=payload.metadata,
    )
    try:
        uow.assets.add(asset)
        uow.flush()
    except IntegrityError as exc:  # pragma: no cover - defensive guard
        uow.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset with this name already exists",
        ) from exc
    return AssetRead.model_validate(asset)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: int,
    include_archived: bool = Query(default=False),
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> AssetRead:
    asset = uow.assets.get(asset_id, include_archived=include_archived)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return AssetRead.model_validate(asset)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> AssetRead:
    asset = uow.assets.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        asset.name = update_data["name"]
    if "asset_group" in update_data:
        asset.asset_group = update_data["asset_group"]
    if "description" in update_data:
        asset.description = update_data["description"]
    if "metadata" in update_data:
        asset.metadata = update_data["metadata"]

    try:
        uow.flush()
    except IntegrityError as exc:  # pragma: no cover - defensive guard
        uow.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset with this name already exists",
        ) from exc

    return AssetRead.model_validate(asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_asset(
    asset_id: int,
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> Response:
    asset = uow.assets.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    uow.assets.archive(asset)
    uow.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
