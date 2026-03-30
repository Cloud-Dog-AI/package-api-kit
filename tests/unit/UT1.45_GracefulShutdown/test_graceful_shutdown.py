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

"""UT1.45: Graceful shutdown request draining and rejection semantics."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cloud_dog_api_kit.correlation import CorrelationMiddleware
from cloud_dog_api_kit.lifecycle.shutdown import GracefulShutdownManager, ShutdownDrainMiddleware


@pytest.mark.asyncio
class TestGracefulShutdown:
    async def test_inflight_requests_are_drained(self) -> None:
        manager = GracefulShutdownManager(drain_timeout_seconds=0.2)
        assert manager.mark_request_started() is True

        shutdown_task = asyncio.create_task(manager.initiate_shutdown())
        await asyncio.sleep(0.01)
        assert manager.shutting_down is True
        assert manager.mark_request_started() is False

        manager.mark_request_finished()
        drained = await shutdown_task
        assert drained is True

    async def test_drain_timeout_returns_false(self) -> None:
        manager = GracefulShutdownManager(drain_timeout_seconds=0.01)
        assert manager.mark_request_started() is True
        drained = await manager.initiate_shutdown()
        manager.mark_request_finished()
        assert drained is False

    async def test_middleware_rejects_new_requests_during_shutdown(self) -> None:
        manager = GracefulShutdownManager(drain_timeout_seconds=0.1)
        manager.set_shutting_down()

        app = FastAPI()
        app.add_middleware(ShutdownDrainMiddleware, manager=manager)
        app.add_middleware(CorrelationMiddleware)

        @app.get("/work")
        async def work() -> dict:
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.get("/work")

        assert response.status_code == 503
        assert response.json()["ok"] is False
