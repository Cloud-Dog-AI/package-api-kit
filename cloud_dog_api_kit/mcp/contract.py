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

# cloud_dog_api_kit — MCP contract registration helper
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: One-call registration helper enforcing MCP catalogue contract.
# Related requirements: FR18.1
# Related architecture: SA1

"""MCP contract registration helper.

Provides a single entry point that registers:
- MCP transport routes (`/mcp`, `/messages`)
- MCP tool catalogue + execution routes (`/mcp/tools`, `/mcp/tools/{tool_name}`)
- Optional legacy read-only catalogue alias (`/tools`)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI

from cloud_dog_api_kit.mcp.session import McpSessionManager
from cloud_dog_api_kit.mcp.tool_router import ToolContract, ToolRegistryType, register_tool_router
from cloud_dog_api_kit.mcp.transport import register_mcp_routes


@dataclass(slots=True)
class MCPContractRegistration:
    """Captured outputs from MCP contract registration."""

    contracts: dict[str, ToolContract]
    session_manager: McpSessionManager


def _catalogue_payload(contracts: dict[str, ToolContract]) -> dict[str, list[dict[str, Any]]]:
    return {
        "tools": [
            {
                "name": contract.name,
                "description": contract.description,
                "input_schema": contract.input_schema,
                "output_schema": contract.output_schema,
            }
            for contract in contracts.values()
        ]
    }


def register_mcp_contract(
    app: FastAPI,
    tool_registry: ToolRegistryType | None,
    transport_modes: list[str] | set[str] | tuple[str, ...] | None = None,
    *,
    include_legacy_tools_alias: bool = True,
    legacy_tools_path: str = "/tools",
    mcp_tools_path: str = "/mcp/tools",
    session_manager: McpSessionManager | None = None,
) -> MCPContractRegistration:
    """Register a complete MCP surface with canonical tool catalogue contract.

    Canonical contract:
    - `GET /mcp/tools` returns tool catalogue (required)
    - `POST /mcp/tools/{tool_name}` executes a tool
    - `POST /mcp` and `POST /messages` provide MCP transport compatibility

    Optional compatibility:
    - `GET /tools` read-only alias for catalogue payload
    """

    contracts = register_tool_router(app, tool_registry, base_path=mcp_tools_path)
    manager = register_mcp_routes(
        app,
        contracts,
        transport_modes=transport_modes,
        session_manager=session_manager,
    )

    if include_legacy_tools_alias:
        if not legacy_tools_path.startswith("/"):
            raise ValueError("legacy_tools_path must start with '/'")
        if legacy_tools_path == mcp_tools_path:
            raise ValueError("legacy_tools_path must differ from mcp_tools_path")

        @app.get(legacy_tools_path, tags=["mcp"])
        async def _legacy_tools_alias() -> dict[str, list[dict[str, Any]]]:
            return _catalogue_payload(contracts)

    return MCPContractRegistration(contracts=contracts, session_manager=manager)
