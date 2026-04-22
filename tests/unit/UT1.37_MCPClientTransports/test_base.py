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

"""UT1.37 base MCP client transport contract coverage."""

from __future__ import annotations

from typing import Any

import pytest

from cloud_dog_api_kit.mcp.client_transport import MCPTransport, MCPTransportError


class _DummyTransport(MCPTransport):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None]] = []
        self.notifications: list[tuple[str, dict[str, Any] | None]] = []

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append((method, params))
        return {"method": method, "params": params or {}}

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self.notifications.append((method, params))


@pytest.mark.asyncio
class TestMCPTransportBase:
    async def test_convenience_methods_delegate_to_request(self) -> None:
        transport = _DummyTransport()

        await transport.tools_list()
        await transport.prompts_list()
        await transport.prompts_get("prompt-name", {"topic": "test"})
        await transport.resources_list()
        await transport.resources_read("file://resource.txt")
        await transport.tools_call("echo", {"value": 1})

        assert transport.calls == [
            ("tools/list", None),
            ("prompts/list", None),
            ("prompts/get", {"name": "prompt-name", "arguments": {"topic": "test"}}),
            ("resources/list", None),
            ("resources/read", {"uri": "file://resource.txt"}),
            ("tools/call", {"name": "echo", "arguments": {"value": 1}}),
        ]

    async def test_initialize_requires_protocol_version(self) -> None:
        transport = _DummyTransport()

        with pytest.raises(MCPTransportError) as exc_info:
            await transport.initialize(protocol_version="")

        assert "protocol_version" in str(exc_info.value)

    async def test_initialize_sends_request_then_notification(self) -> None:
        transport = _DummyTransport()

        await transport.initialize(
            protocol_version="2026-04-01",
            client_name="platform-client",
            client_version="1.2.3",
        )

        assert transport.calls == [
            (
                "initialize",
                {
                    "protocolVersion": "2026-04-01",
                    "clientInfo": {"name": "platform-client", "version": "1.2.3"},
                    "capabilities": {},
                },
            )
        ]
        assert transport.notifications == [("notifications/initialized", None)]
