from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.api.v1 import assets, failure_events, runtime_counters

api_router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])

api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(runtime_counters.router, prefix="/runtime-counters", tags=["runtime-counters"])
api_router.include_router(failure_events.router, prefix="/failure-events", tags=["failure-events"])

__all__ = ["api_router"]
