import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import Asset, Failure, KPISnapshot, RuntimeRecord


class WindowType(str, Enum):
    ROLLING = "rolling"
    CALENDAR = "calendar"


class Granularity(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"


class KPIService:
    """Service for computing KPI metrics (MTBF, MTTR, Availability, Failure Rate)"""

    def __init__(self, db: Session):
        self.db = db

    def compute_and_store_kpis(
        self,
        asset_id: Optional[int] = None,
        asset_group_id: Optional[int] = None,
        window_type: WindowType = WindowType.ROLLING,
        granularity: Granularity = Granularity.DAYS_30,
        evaluation_time: Optional[datetime] = None,
    ) -> list[KPISnapshot]:
        """
        Compute KPIs for specified asset/group and window, then store snapshots.

        Returns list of created/updated KPISnapshot records.
        """
        if evaluation_time is None:
            evaluation_time = datetime.utcnow()

        # Determine window bounds
        window_start, window_end = self._get_window_bounds(
            window_type, granularity, evaluation_time
        )

        # Compute metrics
        metrics = self._compute_metrics(asset_id, asset_group_id, window_start, window_end)

        # Create or update snapshot
        snapshot = self._create_or_update_snapshot(
            asset_id, asset_group_id, window_type, granularity, window_start, window_end, metrics
        )

        return [snapshot]

    def get_latest_kpis(
        self,
        asset_id: Optional[int] = None,
        asset_group_id: Optional[int] = None,
        window_type: Optional[WindowType] = None,
        granularity: Optional[Granularity] = None,
        limit: int = 100,
    ) -> list[KPISnapshot]:
        """Fetch latest KPI snapshots with optional filters."""
        query = self.db.query(KPISnapshot)

        if asset_id:
            query = query.filter(KPISnapshot.asset_id == asset_id)
        if asset_group_id:
            query = query.filter(KPISnapshot.asset_group_id == asset_group_id)
        if window_type:
            query = query.filter(KPISnapshot.window_type == window_type.value)
        if granularity:
            query = query.filter(KPISnapshot.granularity == granularity.value)

        return query.order_by(KPISnapshot.computed_at.desc()).limit(limit).all()

    def _get_window_bounds(
        self,
        window_type: WindowType,
        granularity: Granularity,
        evaluation_time: datetime,
    ) -> Tuple[datetime, datetime]:
        """Calculate window start and end times based on type and granularity."""

        if window_type == WindowType.ROLLING:
            # Rolling windows use trailing intervals from evaluation_time
            if granularity == Granularity.DAYS_7:
                window_start = evaluation_time - timedelta(days=7)
            elif granularity == Granularity.DAYS_30:
                window_start = evaluation_time - timedelta(days=30)
            elif granularity == Granularity.DAYS_90:
                window_start = evaluation_time - timedelta(days=90)
            else:
                raise ValueError(f"Unsupported rolling granularity: {granularity}")
            window_end = evaluation_time

        elif window_type == WindowType.CALENDAR:
            # Calendar windows align to UTC boundaries
            if granularity == Granularity.DAY:
                window_start = evaluation_time.replace(hour=0, minute=0, second=0, microsecond=0)
                window_end = window_start + timedelta(days=1)
            elif granularity == Granularity.WEEK:
                # Start of week (Monday)
                days_since_monday = evaluation_time.weekday()
                window_start = evaluation_time.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=days_since_monday)
                window_end = window_start + timedelta(weeks=1)
            elif granularity == Granularity.MONTH:
                # Start of month
                window_start = evaluation_time.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                # Calculate start of next month
                if evaluation_time.month == 12:
                    next_month = evaluation_time.replace(year=evaluation_time.year + 1, month=1)
                else:
                    next_month = evaluation_time.replace(month=evaluation_time.month + 1)
                window_end = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                raise ValueError(f"Unsupported calendar granularity: {granularity}")
        else:
            raise ValueError(f"Unsupported window type: {window_type}")

        return window_start, window_end

    def _compute_metrics(
        self,
        asset_id: Optional[int],
        asset_group_id: Optional[int],
        window_start: datetime,
        window_end: datetime,
    ) -> dict:
        """Compute raw metrics for the specified window."""

        # Get runtime data
        total_runtime, failure_count, total_downtime = self._get_aggregated_data(
            asset_id, asset_group_id, window_start, window_end
        )

        # Compute KPIs
        metrics = {
            "total_runtime_hours": total_runtime,
            "failure_count": failure_count,
            "total_downtime_hours": total_downtime,
        }

        # MTBF = total_runtime / failure_count
        if failure_count > 0 and total_runtime and total_runtime > 0:
            metrics["mtbf"] = total_runtime / Decimal(failure_count)
            metrics["failure_rate"] = Decimal(1) / metrics["mtbf"]
        else:
            metrics["mtbf"] = None  # Represents infinity when no failures
            metrics["failure_rate"] = (
                Decimal(0) if total_runtime and total_runtime > 0 else Decimal(0)
            )

        # MTTR = total_downtime / failure_count
        if failure_count > 0 and total_downtime:
            metrics["mttr"] = total_downtime / Decimal(failure_count)
        else:
            metrics["mttr"] = None

        # Availability = (total_runtime - downtime) / total_runtime
        if total_runtime and total_runtime > 0:
            downtime = total_downtime or Decimal(0)
            available_time = total_runtime - downtime
            availability = available_time / total_runtime
            # Clamp between 0 and 1
            metrics["availability"] = max(Decimal(0), min(Decimal(1), availability))
        else:
            # When there's no runtime, set availability to 0 if there are failures, None otherwise
            if failure_count > 0:
                metrics["availability"] = Decimal(0)
            else:
                metrics["availability"] = None

        return metrics

    def _get_aggregated_data(
        self,
        asset_id: Optional[int],
        asset_group_id: Optional[int],
        window_start: datetime,
        window_end: datetime,
    ) -> Tuple[Optional[Decimal], int, Optional[Decimal]]:
        """Get aggregated runtime, failure count, and downtime for the window."""

        if asset_id:
            return self._get_asset_aggregated_data(asset_id, window_start, window_end)
        elif asset_group_id:
            return self._get_group_aggregated_data(asset_group_id, window_start, window_end)
        else:
            raise ValueError("Either asset_id or asset_group_id must be provided")

    def _get_asset_aggregated_data(
        self, asset_id: int, window_start: datetime, window_end: datetime
    ) -> Tuple[Optional[Decimal], int, Optional[Decimal]]:
        """Get aggregated data for a single asset."""

        # Runtime data - sum runtime hours for records within window
        runtime_query = self.db.query(func.sum(RuntimeRecord.runtime_hours)).filter(
            RuntimeRecord.asset_id == asset_id,
            RuntimeRecord.start_time < window_end,
            or_(RuntimeRecord.end_time.is_(None), RuntimeRecord.end_time > window_start),
        )
        total_runtime = runtime_query.scalar()

        # Failure count - count failures within window
        failure_count_query = self.db.query(func.count(Failure.id)).filter(
            Failure.asset_id == asset_id,
            Failure.failure_time >= window_start,
            Failure.failure_time < window_end,
        )
        failure_count = failure_count_query.scalar() or 0

        # Downtime - sum downtime for failures within window
        downtime_query = self.db.query(func.sum(Failure.downtime_hours)).filter(
            Failure.asset_id == asset_id,
            Failure.failure_time >= window_start,
            Failure.failure_time < window_end,
            Failure.downtime_hours.is_not(None),
        )
        total_downtime = downtime_query.scalar()

        return total_runtime, failure_count, total_downtime

    def _get_group_aggregated_data(
        self, asset_group_id: int, window_start: datetime, window_end: datetime
    ) -> Tuple[Optional[Decimal], int, Optional[Decimal]]:
        """Get aggregated data for all assets in a group."""

        # Get all assets in the group
        asset_ids_query = self.db.query(Asset.id).filter(Asset.asset_group_id == asset_group_id)
        asset_ids = [row[0] for row in asset_ids_query.all()]

        if not asset_ids:
            return None, 0, None

        # Runtime data - sum across all assets in group
        runtime_query = self.db.query(func.sum(RuntimeRecord.runtime_hours)).filter(
            RuntimeRecord.asset_id.in_(asset_ids),
            RuntimeRecord.start_time < window_end,
            or_(RuntimeRecord.end_time.is_(None), RuntimeRecord.end_time > window_start),
        )
        total_runtime = runtime_query.scalar()

        # Failure count - sum across all assets in group
        failure_count_query = self.db.query(func.count(Failure.id)).filter(
            Failure.asset_id.in_(asset_ids),
            Failure.failure_time >= window_start,
            Failure.failure_time < window_end,
        )
        failure_count = failure_count_query.scalar() or 0

        # Downtime - sum across all assets in group
        downtime_query = self.db.query(func.sum(Failure.downtime_hours)).filter(
            Failure.asset_id.in_(asset_ids),
            Failure.failure_time >= window_start,
            Failure.failure_time < window_end,
            Failure.downtime_hours.is_not(None),
        )
        total_downtime = downtime_query.scalar()

        return total_runtime, failure_count, total_downtime

    def _create_or_update_snapshot(
        self,
        asset_id: Optional[int],
        asset_group_id: Optional[int],
        window_type: WindowType,
        granularity: Granularity,
        window_start: datetime,
        window_end: datetime,
        metrics: dict,
    ) -> KPISnapshot:
        """Create or update KPI snapshot record."""

        # Generate source version hash (for reproducibility)
        source_data = f"{asset_id}-{asset_group_id}-{window_type.value}-{granularity.value}-{window_start}-{window_end}"
        source_version_hash = hashlib.sha256(source_data.encode()).hexdigest()

        # Check if snapshot already exists
        existing = (
            self.db.query(KPISnapshot)
            .filter(
                KPISnapshot.asset_id == asset_id,
                KPISnapshot.asset_group_id == asset_group_id,
                KPISnapshot.window_type == window_type.value,
                KPISnapshot.window_start == window_start,
                KPISnapshot.granularity == granularity.value,
            )
            .first()
        )

        if existing:
            # Update existing snapshot
            existing.window_end = window_end
            existing.mtbf = metrics["mtbf"]
            existing.failure_rate = metrics["failure_rate"]
            existing.mttr = metrics["mttr"]
            existing.availability = metrics["availability"]
            existing.total_runtime_hours = metrics["total_runtime_hours"]
            existing.total_downtime_hours = metrics["total_downtime_hours"]
            existing.failure_count = metrics["failure_count"]
            existing.source_version_hash = source_version_hash
            existing.computed_at = datetime.utcnow()

            snapshot = existing
        else:
            # Create new snapshot
            snapshot = KPISnapshot(
                asset_id=asset_id,
                asset_group_id=asset_group_id,
                window_type=window_type.value,
                window_start=window_start,
                window_end=window_end,
                granularity=granularity.value,
                mtbf=metrics["mtbf"],
                failure_rate=metrics["failure_rate"],
                mttr=metrics["mttr"],
                availability=metrics["availability"],
                total_runtime_hours=metrics["total_runtime_hours"],
                total_downtime_hours=metrics["total_downtime_hours"],
                failure_count=metrics["failure_count"],
                source_version_hash=source_version_hash,
            )
            self.db.add(snapshot)

        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot
