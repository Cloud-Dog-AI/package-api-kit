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

"""UT1.36: MCP transport route registration and mode compatibility."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cloud_dog_api_kit.mcp.session import SESSION_HEADER
from cloud_dog_api_kit.mcp.transport import register_mcp_routes


async def _echo_tool(payload: dict, _request) -> dict:
    return {"echo": payload}


@pytest.mark.asyncio
class TestMCPTransportHelpers:
    async def test_register_routes_and_call_tool(self) -> None:
        app = FastAPI()
        register_mcp_routes(
            app,
            {"echo": _echo_tool},
            transport_modes={"streamable_http", "http_jsonrpc", "legacy_sse", "stdio"},
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/mcp", json={"tool": "echo", "arguments": {"value": 1}})

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["data"]["echo"]["value"] == 1
        assert response.headers.get(SESSION_HEADER)

    async def test_jsonrpc_via_messages_alias(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"http_jsonrpc"})

        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"value": "x"}},
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/messages", json=payload)

        assert response.status_code == 200
        assert response.json()["data"]["echo"]["value"] == "x"

    async def test_unknown_tool_returns_404_envelope(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"streamable_http"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/mcp", json={"tool": "missing", "arguments": {}})

        assert response.status_code == 404
        assert response.json()["ok"] is False
        assert response.json()["error"]["code"] == "NOT_FOUND"

    async def test_legacy_sse_mode_exposes_event_stream(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"legacy_sse"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.get("/mcp")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
