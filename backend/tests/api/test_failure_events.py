from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_failure_event_and_patch(async_client: AsyncClient, create_asset) -> None:
    asset_id = create_asset("CNC", "machining")
    occurred = datetime(2024, 2, 1, 8, 0, tzinfo=timezone.utc)
    resolved = occurred + timedelta(hours=2, minutes=30)

    create_response = await async_client.post(
        "/api/v1/failure-events",
        json={
            "asset_id": asset_id,
            "occurred_at": occurred.isoformat(),
            "resolved_at": resolved.isoformat(),
            "description": "Spindle error",
            "metadata": {"code": "E42"},
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["downtime_minutes"] == 150

    updated_resolved = resolved + timedelta(hours=1)
    patch_response = await async_client.patch(
        f"/api/v1/failure-events/{created['id']}",
        json={"resolved_at": updated_resolved.isoformat()},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["downtime_minutes"] == 210


@pytest.mark.asyncio
async def test_failure_event_patch_validation(async_client: AsyncClient, create_asset) -> None:
    asset_id = create_asset("Oven", "heat")
    occurred = datetime(2024, 3, 1, tzinfo=timezone.utc)
    create_response = await async_client.post(
        "/api/v1/failure-events",
        json={
            "asset_id": asset_id,
            "occurred_at": occurred.isoformat(),
            "description": "Overheat",
        },
    )
    failure_id = create_response.json()["id"]

    invalid_patch = await async_client.patch(
        f"/api/v1/failure-events/{failure_id}",
        json={"resolved_at": (occurred - timedelta(minutes=5)).isoformat()},
    )
    assert invalid_patch.status_code == 400
    assert "resolved_at" in invalid_patch.json()["detail"]

    await async_client.patch(
        f"/api/v1/failure-events/{failure_id}",
        json={"resolved_at": (occurred + timedelta(hours=1)).isoformat()},
    )

    invalid_patch_2 = await async_client.patch(
        f"/api/v1/failure-events/{failure_id}",
        json={"occurred_at": (occurred + timedelta(hours=2)).isoformat()},
    )
    assert invalid_patch_2.status_code == 400
    assert "resolved_at" in invalid_patch_2.json()["detail"]


@pytest.mark.asyncio
async def test_failure_event_date_filters(async_client: AsyncClient, create_asset) -> None:
    asset_id = create_asset("Pump", "water")
    start_time = datetime(2024, 4, 1, tzinfo=timezone.utc)

    for offset in range(3):
        await async_client.post(
            "/api/v1/failure-events",
            json={
                "asset_id": asset_id,
                "occurred_at": (start_time + timedelta(days=offset)).isoformat(),
                "description": f"Failure {offset}",
            },
        )

    response = await async_client.get(
        "/api/v1/failure-events",
        params={
            "asset_id": asset_id,
            "start": (start_time + timedelta(days=1)).isoformat(),
            "end": (start_time + timedelta(days=1, hours=1)).isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 1
    assert data["items"][0]["description"] == "Failure 1"


@pytest.mark.asyncio
async def test_failure_event_archive(async_client: AsyncClient, create_asset) -> None:
    asset_id = create_asset("Compressor", "air")
    occurred = datetime(2024, 5, 1, tzinfo=timezone.utc)
    create_response = await async_client.post(
        "/api/v1/failure-events",
        json={
            "asset_id": asset_id,
            "occurred_at": occurred.isoformat(),
            "description": "Seal leak",
        },
    )
    failure_id = create_response.json()["id"]

    delete_response = await async_client.delete(f"/api/v1/failure-events/{failure_id}")
    assert delete_response.status_code == 204

    get_response = await async_client.get(f"/api/v1/failure-events/{failure_id}")
    assert get_response.status_code == 404

    get_archived = await async_client.get(
        f"/api/v1/failure-events/{failure_id}", params={"include_archived": True}
    )
    assert get_archived.status_code == 200
    assert get_archived.json()["is_archived"] is True


@pytest.mark.asyncio
async def test_failure_event_not_found(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/failure-events/9999")
    assert response.status_code == 404
