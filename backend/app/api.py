from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.kpi_service import Granularity, KPIService, WindowType
from app.models import Asset as AssetModel
from app.models import AssetGroup as AssetGroupModel
from app.models import Failure as FailureModel
from app.models import RuntimeRecord as RuntimeRecordModel
from app.schemas import (
    Asset,
    AssetCreate,
    AssetGroup,
    AssetGroupCreate,
    Failure,
    FailureCreate,
    FailureUpdate,
    KPIRequest,
    KPIResponse,
    KPISnapshot,
    RuntimeRecord,
    RuntimeRecordCreate,
)

router = APIRouter(prefix="/api/v1", tags=["kpis"])


# KPI Endpoints
@router.post("/kpis/compute", response_model=List[KPISnapshot])
async def compute_kpis(
    request: KPIRequest,
    db: Session = Depends(get_db),
):
    """
    Compute KPIs for specified asset or asset group.

    - **asset_id**: Compute KPIs for specific asset (optional)
    - **asset_group_id**: Compute KPIs for asset group (optional)
    - **window_type**: 'rolling' or 'calendar'
    - **granularity**: 'day', 'week', 'month', '7d', '30d', '90d'
    - **evaluation_time**: Reference time for window calculation (defaults to now)

    Either asset_id or asset_group_id must be provided.
    """
    if not request.asset_id and not request.asset_group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either asset_id or asset_group_id must be provided",
        )

    try:
        window_type = WindowType(request.window_type)
        granularity = Granularity(request.granularity)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid window type or granularity: {str(e)}",
        ) from e

    kpi_service = KPIService(db)
    snapshots = kpi_service.compute_and_store_kpis(
        asset_id=request.asset_id,
        asset_group_id=request.asset_group_id,
        window_type=window_type,
        granularity=granularity,
        evaluation_time=request.evaluation_time,
    )

    return snapshots


@router.get("/kpis", response_model=KPIResponse)
async def get_kpis(
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    asset_group_id: Optional[int] = Query(None, description="Filter by asset group ID"),
    window_type: Optional[str] = Query(
        None, pattern=r"^(rolling|calendar)$", description="Filter by window type"
    ),
    granularity: Optional[str] = Query(
        None, pattern=r"^(day|week|month|7d|30d|90d)$", description="Filter by granularity"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db),
):
    """
    Get latest KPI snapshots with optional filters.

    Returns KPI metrics with window metadata and provenance data.
    Metrics are rounded to 3 decimal places for display purposes.
    """
    kpi_service = KPIService(db)

    # Convert string enums to proper types if provided
    window_type_enum = WindowType(window_type) if window_type else None
    granularity_enum = Granularity(granularity) if granularity else None

    snapshots = kpi_service.get_latest_kpis(
        asset_id=asset_id,
        asset_group_id=asset_group_id,
        window_type=window_type_enum,
        granularity=granularity_enum,
        limit=limit,
    )

    return KPIResponse(snapshots=snapshots, total=len(snapshots))


# Asset Management Endpoints
@router.post("/assets", response_model=Asset)
async def create_asset(
    asset: AssetCreate,
    db: Session = Depends(get_db),
):
    """Create a new asset."""
    db_asset = AssetModel(**asset.model_dump())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


@router.get("/assets", response_model=List[Asset])
async def list_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    asset_group_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """List assets with optional filters."""
    query = db.query(AssetModel)

    if asset_group_id:
        query = query.filter(AssetModel.asset_group_id == asset_group_id)
    if is_active is not None:
        query = query.filter(AssetModel.is_active == is_active)

    assets = query.offset(skip).limit(limit).all()
    return assets


@router.get("/assets/{asset_id}", response_model=Asset)
async def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
):
    """Get asset by ID."""
    asset = db.query(AssetModel).filter(AssetModel.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


# Asset Group Management Endpoints
@router.post("/asset-groups", response_model=AssetGroup)
async def create_asset_group(
    asset_group: AssetGroupCreate,
    db: Session = Depends(get_db),
):
    """Create a new asset group."""
    db_group = AssetGroupModel(**asset_group.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


@router.get("/asset-groups", response_model=List[AssetGroup])
async def list_asset_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List asset groups."""
    groups = db.query(AssetGroupModel).offset(skip).limit(limit).all()
    return groups


@router.get("/asset-groups/{group_id}", response_model=AssetGroup)
async def get_asset_group(
    group_id: int,
    db: Session = Depends(get_db),
):
    """Get asset group by ID."""
    group = db.query(AssetGroupModel).filter(AssetGroupModel.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset group not found")
    return group


# Runtime Record Endpoints
@router.post("/runtime-records", response_model=RuntimeRecord)
async def create_runtime_record(
    record: RuntimeRecordCreate,
    db: Session = Depends(get_db),
):
    """Create a new runtime record."""
    db_record = RuntimeRecordModel(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


@router.get("/assets/{asset_id}/runtime-records", response_model=List[RuntimeRecord])
async def get_asset_runtime_records(
    asset_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get runtime records for an asset."""
    records = (
        db.query(RuntimeRecordModel)
        .filter(RuntimeRecordModel.asset_id == asset_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return records


# Failure Management Endpoints
@router.post("/failures", response_model=Failure)
async def create_failure(
    failure: FailureCreate,
    db: Session = Depends(get_db),
):
    """Create a new failure record."""
    db_failure = FailureModel(**failure.model_dump())
    db.add(db_failure)
    db.commit()
    db.refresh(db_failure)
    return db_failure


@router.get("/assets/{asset_id}/failures", response_model=List[Failure])
async def get_asset_failures(
    asset_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_resolved: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Get failure records for an asset."""
    query = db.query(FailureModel).filter(FailureModel.asset_id == asset_id)

    if is_resolved is not None:
        query = query.filter(FailureModel.is_resolved == is_resolved)

    failures = query.offset(skip).limit(limit).all()
    return failures


@router.put("/failures/{failure_id}", response_model=Failure)
async def update_failure(
    failure_id: int,
    failure_update: FailureUpdate,
    db: Session = Depends(get_db),
):
    """Update a failure record."""
    db_failure = db.query(FailureModel).filter(FailureModel.id == failure_id).first()
    if not db_failure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failure not found")

    update_data = failure_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_failure, field, value)

    db.commit()
    db.refresh(db_failure)
    return db_failure
