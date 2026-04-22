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

"""UT1.37 streamable HTTP MCP transport coverage."""

from __future__ import annotations

import httpx
import pytest

from cloud_dog_api_kit.mcp.client_transport import (
    MCPSessionError,
    StreamableHTTPConfig,
    StreamableHTTPTransport,
)
from cloud_dog_api_kit.mcp.session import SESSION_HEADER


@pytest.mark.asyncio
class TestStreamableHTTPTransport:
    async def test_ensure_sse_noop_when_disabled(self) -> None:
        transport = StreamableHTTPTransport(
            StreamableHTTPConfig(
                base_url="http://localhost:3000",
                mcp_path="/mcp",
                enable_sse=False,
                timeout_seconds=1.0,
            )
        )

        await transport.ensure_sse_stream()

    async def test_connect_uses_shared_httpx_client_with_trust_env(self) -> None:
        transport = StreamableHTTPTransport(
            StreamableHTTPConfig(
                base_url="http://localhost:3000",
                mcp_path="/mcp",
                timeout_seconds=1.0,
            )
        )

        await transport.connect()
        try:
            first_client = transport._client
            assert first_client is not None
            assert first_client.trust_env is True

            await transport.connect()
            assert transport._client is first_client
        finally:
            await transport.close()

    async def test_tools_list_captures_session_and_normalises_payload(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path == "/mcp":
                return httpx.Response(
                    200,
                    headers={SESSION_HEADER: "sess-stream-1"},
                    json={"tools": [{"name": "echo"}]},
                )
            if request.method == "GET" and request.url.path == "/mcp":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/event-stream"},
                    text='event: ready\ndata: {"ready": true}\n\n',
                )
            raise AssertionError(f"Unexpected request: {request.method} {request.url}")

        transport = StreamableHTTPTransport(
            StreamableHTTPConfig(
                base_url="http://mcp.example",
                mcp_path="/mcp",
                timeout_seconds=1.0,
            )
        )
        transport._client = httpx.AsyncClient(
            base_url="http://mcp.example",
            transport=httpx.MockTransport(handler),
            trust_env=True,
        )

        try:
            result = await transport.tools_list()
        finally:
            await transport.close()

        assert result == {"tools": [{"name": "echo"}]}
        assert transport._session_id == "sess-stream-1"

    async def test_terminate_session_requires_active_session(self) -> None:
        transport = StreamableHTTPTransport(
            StreamableHTTPConfig(
                base_url="http://mcp.example",
                mcp_path="/mcp",
                timeout_seconds=1.0,
            )
        )

        with pytest.raises(MCPSessionError):
            await transport.terminate_session()
