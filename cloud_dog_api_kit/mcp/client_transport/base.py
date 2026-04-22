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

# cloud_dog_api_kit — MCP client transport base
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Abstract MCP client transport contract shared by HTTP, SSE,
#   and stdio implementations.
# Related requirements: FR18.1
# Related architecture: SA1

"""Base MCP client transport contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .exceptions import MCPTransportError


class MCPTransport(ABC):
    """Abstract base for MCP client transport implementations."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish the underlying transport connection."""

    @abstractmethod
    async def close(self) -> None:
        """Close transport resources and pending sessions."""

    @abstractmethod
    async def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send an MCP request and return a JSON-RPC result object."""

    @abstractmethod
    async def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a fire-and-forget MCP notification."""

    async def tools_list(self) -> Dict[str, Any]:
        """Request the server's MCP tool list."""
        return await self.request("tools/list")

    async def prompts_list(self) -> Dict[str, Any]:
        """Request the server's MCP prompt catalogue."""
        return await self.request("prompts/list")

    async def prompts_get(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Request a specific prompt from the server."""
        params: Dict[str, Any] = {"name": name}
        if arguments is not None:
            params["arguments"] = arguments
        return await self.request("prompts/get", params=params)

    async def resources_list(self) -> Dict[str, Any]:
        """Request the server's MCP resource catalogue."""
        return await self.request("resources/list")

    async def resources_read(self, uri: str) -> Dict[str, Any]:
        """Request a specific MCP resource by URI."""
        return await self.request("resources/read", params={"uri": uri})

    async def tools_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke an MCP tool."""
        return await self.request("tools/call", params={"name": name, "arguments": arguments})

    async def initialize(
        self,
        *,
        protocol_version: str,
        client_name: str = "cloud-dog-chat-client",
        client_version: str = "0.1.0",
    ) -> None:
        """Perform the standard MCP initialise + notifications/initialized flow."""
        if not protocol_version:
            raise MCPTransportError("MCP initialize requires protocol_version")
        await self.request(
            "initialize",
            params={
                "protocolVersion": protocol_version,
                "clientInfo": {"name": client_name, "version": client_version},
                "capabilities": {},
            },
        )
        await self.notify("notifications/initialized")
