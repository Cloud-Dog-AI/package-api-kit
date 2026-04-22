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

# cloud_dog_api_kit — MCP client transport exceptions
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Shared exception hierarchy for MCP client transport adapters.
# Related requirements: FR18.1
# Related architecture: SA1

"""Exceptions raised by MCP client transports."""

from __future__ import annotations


class MCPTransportError(RuntimeError):
    """Raised when an MCP transport operation fails."""


class MCPSessionError(MCPTransportError):
    """Raised when an MCP transport session lifecycle operation fails."""


class MCPProtocolError(MCPTransportError):
    """Raised when a peer violates the expected MCP protocol contract."""
