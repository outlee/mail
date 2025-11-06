from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_runtime_counter_delta_computation(async_client: AsyncClient, create_asset) -> None:
    asset_id = create_asset("Turbine", "power")
    base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

    first_payload = {
        "asset_id": asset_id,
        "recorded_at": base_time.isoformat(),
        "total_hours": 120.0,
    }
    first_response = await async_client.post("/api/v1/runtime-counters", json=first_payload)
    assert first_response.status_code == 201
    first = first_response.json()
    assert first["delta_hours"] == pytest.approx(120.0)

    second_payload = {
        "asset_id": asset_id,
        "recorded_at": (base_time + timedelta(hours=12)).isoformat(),
        "total_hours": 175.5,
    }
    second_response = await async_client.post("/api/v1/runtime-counters", json=second_payload)
    assert second_response.status_code == 201
    second = second_response.json()
    assert second["delta_hours"] == pytest.approx(55.5)


@pytest.mark.asyncio
async def test_runtime_counter_list_aggregation(async_client: AsyncClient, create_asset) -> None:
    asset_id = create_asset("Press", "stamping")
    base_time = datetime(2024, 5, 10, tzinfo=timezone.utc)
    await async_client.post(
        "/api/v1/runtime-counters",
        json={
            "asset_id": asset_id,
            "recorded_at": base_time.isoformat(),
            "total_hours": 50.0,
        },
    )
    await async_client.post(
        "/api/v1/runtime-counters",
        json={
            "asset_id": asset_id,
            "recorded_at": (base_time + timedelta(days=1)).isoformat(),
            "total_hours": 110.0,
        },
    )
    await async_client.post(
        "/api/v1/runtime-counters",
        json={
            "asset_id": asset_id,
            "recorded_at": (base_time + timedelta(days=2)).isoformat(),
            "total_hours": 150.0,
        },
    )

    response = await async_client.get(
        "/api/v1/runtime-counters",
        params={
            "asset_id": asset_id,
            "start": (base_time + timedelta(hours=1)).isoformat(),
            "end": (base_time + timedelta(days=2, hours=1)).isoformat(),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 2
    assert payload["delta_hours_total"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_runtime_counter_update_validation(async_client: AsyncClient, create_asset) -> None:
    asset_id = create_asset("Shaper", "metal")
    recorded_at = datetime(2024, 6, 1, tzinfo=timezone.utc)

    create_resp = await async_client.post(
        "/api/v1/runtime-counters",
        json={
            "asset_id": asset_id,
            "recorded_at": recorded_at.isoformat(),
            "total_hours": 20.0,
        },
    )
    counter_id = create_resp.json()["id"]

    error_response = await async_client.patch(
        f"/api/v1/runtime-counters/{counter_id}",
        json={"total_hours": -1},
    )
    assert error_response.status_code == 422

    await async_client.post(
        "/api/v1/runtime-counters",
        json={
            "asset_id": asset_id,
            "recorded_at": (recorded_at + timedelta(hours=1)).isoformat(),
            "total_hours": 30.0,
        },
    )

    invalid_update = await async_client.patch(
        f"/api/v1/runtime-counters/{counter_id}",
        json={"total_hours": 10.0},
    )
    assert invalid_update.status_code == 400
    assert "previous entry" in invalid_update.json()["detail"].lower()


@pytest.mark.asyncio
async def test_runtime_counter_archive_adjusts_next_delta(async_client: AsyncClient, create_asset) -> None:
    asset_id = create_asset("Line A", "assembly")
    base_time = datetime(2024, 7, 1, tzinfo=timezone.utc)

    first = await async_client.post(
        "/api/v1/runtime-counters",
        json={
            "asset_id": asset_id,
            "recorded_at": base_time.isoformat(),
            "total_hours": 100.0,
        },
    )
    first_id = first.json()["id"]

    middle = await async_client.post(
        "/api/v1/runtime-counters",
        json={
            "asset_id": asset_id,
            "recorded_at": (base_time + timedelta(hours=4)).isoformat(),
            "total_hours": 140.0,
        },
    )
    middle_id = middle.json()["id"]

    latest = await async_client.post(
        "/api/v1/runtime-counters",
        json={
            "asset_id": asset_id,
            "recorded_at": (base_time + timedelta(hours=8)).isoformat(),
            "total_hours": 200.0,
        },
    )
    latest_id = latest.json()["id"]

    archive_response = await async_client.delete(f"/api/v1/runtime-counters/{middle_id}")
    assert archive_response.status_code == 204

    latest_fetch = await async_client.get(f"/api/v1/runtime-counters/{latest_id}")
    assert latest_fetch.status_code == 200
    assert latest_fetch.json()["delta_hours"] == pytest.approx(100.0)

    first_fetch = await async_client.get(f"/api/v1/runtime-counters/{first_id}")
    assert first_fetch.status_code == 200


@pytest.mark.asyncio
async def test_runtime_counter_not_found(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/runtime-counters/9999")
    assert response.status_code == 404
