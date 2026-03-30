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

"""UT1.37: MCP tool router typed contract and dispatch tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cloud_dog_api_kit.mcp.tool_router import register_tool_router


def _sum_handler(payload: dict) -> dict:
    return {"result": int(payload["a"]) + int(payload["b"])}


@pytest.mark.asyncio
class TestMCPToolRouter:
    async def test_list_tools_with_contract_metadata(self) -> None:
        app = FastAPI()
        register_tool_router(
            app,
            {
                "sum": {
                    "handler": _sum_handler,
                    "description": "Sum two integers",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                }
            },
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.get("/mcp/tools")

        assert response.status_code == 200
        tools = response.json()["data"]
        assert tools[0]["name"] == "sum"
        assert tools[0]["description"] == "Sum two integers"

    async def test_call_known_tool(self) -> None:
        app = FastAPI()
        register_tool_router(app, {"sum": _sum_handler})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/mcp/tools/sum", json={"a": 2, "b": 3})

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["data"]["result"] == 5

    async def test_unknown_tool_returns_404(self) -> None:
        app = FastAPI()
        register_tool_router(app, {"sum": _sum_handler})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/mcp/tools/missing", json={})

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
