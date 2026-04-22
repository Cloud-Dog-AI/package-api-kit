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

# cloud_dog_api_kit — MCP client transport exports
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Public exports for MCP client transport implementations.
# Related requirements: FR18.1
# Related architecture: SA1

"""Public exports for MCP client transports."""

from __future__ import annotations

from .base import MCPTransport, MCPTransportError
from .exceptions import MCPProtocolError, MCPSessionError
from .http_jsonrpc import HTTPJSONRPCConfig, HTTPJSONRPCTransport
from .legacy_sse import LegacySSEConfig, LegacySSETransport
from .stdio import StdioConfig, StdioTransport
from .streamable_http import StreamableHTTPConfig, StreamableHTTPTransport

__all__ = [
    "HTTPJSONRPCConfig",
    "HTTPJSONRPCTransport",
    "LegacySSEConfig",
    "LegacySSETransport",
    "MCPProtocolError",
    "MCPSessionError",
    "MCPTransport",
    "MCPTransportError",
    "StdioConfig",
    "StdioTransport",
    "StreamableHTTPConfig",
    "StreamableHTTPTransport",
]
