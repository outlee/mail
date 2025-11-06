from __future__ import annotations

from httpx import AsyncClient
import pytest

from app.auth import API_KEY_HEADER, API_KEY_VALUE
from app.main import app


@pytest.mark.asyncio
async def test_create_and_get_asset(async_client: AsyncClient) -> None:
    payload = {
        "name": "Generator Alpha",
        "asset_group": "power",
        "description": "Primary generator",
        "metadata": {"voltage": "480V"},
    }

    create_response = await async_client.post("/api/v1/assets", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == payload["name"]
    assert created["metadata"] == payload["metadata"]

    asset_id = created["id"]
    get_response = await async_client.get(f"/api/v1/assets/{asset_id}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["id"] == asset_id
    assert fetched["asset_group"] == payload["asset_group"]


@pytest.mark.asyncio
async def test_list_assets_with_filters(async_client: AsyncClient, create_asset) -> None:
    create_asset("Pump A", "water")
    create_asset("Pump B", "water")
    create_asset("Compressor", "air")

    response = await async_client.get("/api/v1/assets", params={"asset_group": "water", "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 2
    names = {item["name"] for item in data["items"]}
    assert names == {"Pump A", "Pump B"}


@pytest.mark.asyncio
async def test_update_asset_validation(async_client: AsyncClient) -> None:
    payload = {"name": "Boiler", "asset_group": "steam"}
    create_response = await async_client.post("/api/v1/assets", json=payload)
    asset_id = create_response.json()["id"]

    update_response = await async_client.patch(f"/api/v1/assets/{asset_id}", json={})
    assert update_response.status_code == 422


@pytest.mark.asyncio
async def test_archive_asset(async_client: AsyncClient) -> None:
    payload = {"name": "Fan", "asset_group": "hvac"}
    create_response = await async_client.post("/api/v1/assets", json=payload)
    asset_id = create_response.json()["id"]

    delete_response = await async_client.delete(f"/api/v1/assets/{asset_id}")
    assert delete_response.status_code == 204

    get_response = await async_client.get(f"/api/v1/assets/{asset_id}")
    assert get_response.status_code == 404

    get_archived = await async_client.get(
        f"/api/v1/assets/{asset_id}", params={"include_archived": True}
    )
    assert get_archived.status_code == 200
    assert get_archived.json()["is_archived"] is True


@pytest.mark.asyncio
async def test_asset_requires_api_key() -> None:
    async with AsyncClient(app=app, base_url="http://test") as unauthenticated_client:
        response = await unauthenticated_client.get("/api/v1/assets")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"

    async with AsyncClient(app=app, base_url="http://test") as authenticated_client:
        authenticated_client.headers[API_KEY_HEADER] = API_KEY_VALUE
        response = await authenticated_client.get("/api/v1/assets")
    assert response.status_code == 200
