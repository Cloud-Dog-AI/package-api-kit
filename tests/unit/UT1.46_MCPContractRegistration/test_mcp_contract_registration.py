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

"""UT1.46: register_mcp_contract() enforces MCP tool catalogue contract."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cloud_dog_api_kit.mcp.contract import register_mcp_contract


def _echo_tool(payload: dict) -> dict:
    return {"echo": payload}


@pytest.mark.asyncio
class TestMCPContractRegistration:
    async def test_registers_canonical_mcp_catalogue_and_transport_routes(self) -> None:
        app = FastAPI()
        register_mcp_contract(app, {"echo": _echo_tool})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            catalogue = await client.get("/mcp/tools")
            called = await client.post("/mcp/tools/echo", json={"value": "ok"})
            transport = await client.post("/mcp", json={"tool": "echo", "arguments": {"value": 7}})

        assert catalogue.status_code == 200
        assert [tool["name"] for tool in catalogue.json()["data"]] == ["echo"]
        assert called.status_code == 200
        assert called.json()["data"]["echo"]["value"] == "ok"
        assert transport.status_code == 200
        assert transport.json()["data"]["echo"]["value"] == 7

    async def test_legacy_tools_alias_is_optional(self) -> None:
        app = FastAPI()
        register_mcp_contract(app, {"echo": _echo_tool}, include_legacy_tools_alias=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            legacy = await client.get("/tools")

        assert legacy.status_code == 404

    async def test_legacy_tools_alias_payload_shape(self) -> None:
        app = FastAPI()
        register_mcp_contract(app, {"echo": _echo_tool}, include_legacy_tools_alias=True)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            legacy = await client.get("/tools")

        assert legacy.status_code == 200
        assert [tool["name"] for tool in legacy.json()["tools"]] == ["echo"]
