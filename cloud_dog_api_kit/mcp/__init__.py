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

# cloud_dog_api_kit — MCP gateway
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: REST-to-MCP gateway helpers.
# Related requirements: FR14.1
# Related architecture: SA1

"""MCP gateway helpers for cloud_dog_api_kit."""

from __future__ import annotations

from cloud_dog_api_kit.mcp.client_transport import (
    HTTPJSONRPCConfig,
    HTTPJSONRPCTransport,
    LegacySSETransport,
    MCPProtocolError,
    MCPSessionError,
    MCPTransport,
    MCPTransportError,
    StdioConfig,
    StdioTransport,
    StreamableHTTPConfig,
    StreamableHTTPTransport,
)
from cloud_dog_api_kit.mcp.async_jobs import AsyncJobStore, InMemoryAsyncJobStore
from cloud_dog_api_kit.mcp.gateway import MCPToolDefinition, create_mcp_tool_from_endpoint
from cloud_dog_api_kit.mcp.contract import MCPContractRegistration, register_mcp_contract
from cloud_dog_api_kit.mcp.error_mapper import map_legacy_mcp_payload
from cloud_dog_api_kit.mcp.legacy_sse import LegacySSEConfig
from cloud_dog_api_kit.mcp.session import SESSION_HEADER, McpSession, McpSessionManager
from cloud_dog_api_kit.mcp.tool_router import ToolContract, register_tool_router
from cloud_dog_api_kit.mcp.transport import register_mcp_routes

__all__ = [
    "AsyncJobStore",
    "InMemoryAsyncJobStore",
    "MCPContractRegistration",
    "MCPToolDefinition",
    "MCPProtocolError",
    "MCPSessionError",
    "MCPTransport",
    "MCPTransportError",
    "McpSession",
    "McpSessionManager",
    "SESSION_HEADER",
    "HTTPJSONRPCConfig",
    "HTTPJSONRPCTransport",
    "LegacySSEConfig",
    "LegacySSETransport",
    "StdioConfig",
    "StdioTransport",
    "StreamableHTTPConfig",
    "StreamableHTTPTransport",
    "ToolContract",
    "create_mcp_tool_from_endpoint",
    "map_legacy_mcp_payload",
    "register_mcp_contract",
    "register_mcp_routes",
    "register_tool_router",
]
