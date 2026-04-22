# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""UT1.16: CRUD Router — standard CRUD route generation tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.routers.crud import create_crud_router
from cloud_dog_api_kit.errors import register_error_handlers
from cloud_dog_api_kit.correlation import CorrelationMiddleware
from tests.conftest import ItemModel, InMemoryCRUDService


def _create_app() -> tuple[FastAPI, InMemoryCRUDService]:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    register_error_handlers(app)
    svc = InMemoryCRUDService()
    router = create_crud_router("items", ItemModel, svc)
    app.include_router(router)
    return app, svc


@pytest.mark.asyncio
class TestCRUDRouter:
    async def test_create_resource(self) -> None:
        app, _ = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/items", json={"name": "Widget", "status": "active"})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["data"]["name"] == "Widget"
        assert "id" in body["data"]

    async def test_get_resource(self) -> None:
        app, svc = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            cr = await c.post("/items", json={"name": "A"})
            rid = cr.json()["data"]["id"]
            r = await c.get(f"/items/{rid}")
        assert r.status_code == 200
        assert r.json()["data"]["id"] == rid

    async def test_get_not_found(self) -> None:
        app, _ = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/items/nonexistent")
        assert r.status_code == 404

    async def test_list_resources(self) -> None:
        app, _ = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/items", json={"name": "A"})
            await c.post("/items", json={"name": "B"})
            r = await c.get("/items")
        body = r.json()
        assert body["ok"] is True
        assert len(body["data"]["items"]) == 2
        assert "page" in body["data"]

    async def test_update_resource(self) -> None:
        app, _ = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            cr = await c.post("/items", json={"name": "Old"})
            rid = cr.json()["data"]["id"]
            r = await c.patch(f"/items/{rid}", json={"name": "New"})
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "New"

    async def test_delete_resource(self) -> None:
        app, _ = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            cr = await c.post("/items", json={"name": "Del"})
            rid = cr.json()["data"]["id"]
            r = await c.delete(f"/items/{rid}")
        assert r.status_code == 200
        assert r.json()["data"]["deleted"] is True

    async def test_delete_not_found(self) -> None:
        app, _ = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.delete("/items/nope")
        assert r.status_code == 404
