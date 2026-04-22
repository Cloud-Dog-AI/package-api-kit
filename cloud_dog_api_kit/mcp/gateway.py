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

# cloud_dog_api_kit — MCP gateway helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Helpers for mapping REST endpoints to MCP tool definitions.
#   MCP tools MUST map directly to REST endpoints and share schemas.
# Related requirements: FR14.1
# Related architecture: CC1.18

"""MCP gateway helpers for cloud_dog_api_kit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPToolDefinition:
    """MCP tool definition mapped from a REST endpoint.

    Attributes:
        name: The tool name (derived from endpoint path).
        description: Human-readable description.
        endpoint_path: The REST endpoint path this tool maps to.
        method: HTTP method. Defaults to ``POST``.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.

    Related tests: UT1.32_MCPGateway
    """

    name: str
    description: str
    endpoint_path: str
    method: str = "POST"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary suitable for MCP tool registration.

        Returns:
            A dictionary with the tool definition.
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
        }


def create_mcp_tool_from_endpoint(
    endpoint_path: str,
    method: str = "POST",
    description: str = "",
    name: str | None = None,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> MCPToolDefinition:
    """Create an MCP tool definition from a REST endpoint.

    The tool name is derived from the endpoint path if not provided
    (e.g., ``/api/v1/users`` becomes ``users``).

    Args:
        endpoint_path: The REST endpoint path.
        method: HTTP method. Defaults to ``POST``.
        description: Tool description.
        name: Override tool name. Derived from path if None.
        input_schema: JSON Schema for inputs.
        output_schema: JSON Schema for outputs.

    Returns:
        An MCPToolDefinition instance.

    Related tests: UT1.32_MCPGateway
    """
    if name is None:
        # Derive name from path: /api/v1/users/{id}:run -> users_run
        parts = endpoint_path.strip("/").split("/")
        # Skip version prefix
        filtered = [p for p in parts if not p.startswith("{") and p not in ("api", "v1", "v2")]
        name = "_".join(filtered).replace(":", "_")

    return MCPToolDefinition(
        name=name,
        description=description,
        endpoint_path=endpoint_path,
        method=method,
        input_schema=input_schema or {},
        output_schema=output_schema or {},
    )
