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

"""UT1.19: Job Router — job submission endpoint tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.routers.jobs import create_job_endpoint
from cloud_dog_api_kit.correlation import CorrelationMiddleware


async def _submit(body: dict) -> str:
    return "job-001"


@pytest.mark.asyncio
class TestJobRouter:
    async def test_submit_returns_job_id(self) -> None:
        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)
        app.include_router(create_job_endpoint("queries", _submit))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/queries:run", json={"sql": "SELECT 1"})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["data"]["job_id"] == "job-001"
