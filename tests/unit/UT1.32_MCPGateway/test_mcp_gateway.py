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

"""UT1.32: MCP Gateway — MCP tool definition mapping tests."""

from __future__ import annotations
from cloud_dog_api_kit.mcp.gateway import MCPToolDefinition, create_mcp_tool_from_endpoint


class TestMCPGateway:
    def test_create_tool_from_endpoint(self) -> None:
        tool = create_mcp_tool_from_endpoint("/api/v1/users", description="List users")
        assert tool.name == "users"
        assert tool.endpoint_path == "/api/v1/users"

    def test_custom_name(self) -> None:
        tool = create_mcp_tool_from_endpoint("/api/v1/search", name="web_search")
        assert tool.name == "web_search"

    def test_to_dict(self) -> None:
        tool = MCPToolDefinition(
            name="test", description="A test", endpoint_path="/test", input_schema={"type": "object"}
        )
        d = tool.to_dict()
        assert d["name"] == "test"
        assert d["inputSchema"] == {"type": "object"}

    def test_derived_name_strips_version(self) -> None:
        tool = create_mcp_tool_from_endpoint("/api/v1/queries")
        assert tool.name == "queries"

    def test_derived_name_with_action(self) -> None:
        tool = create_mcp_tool_from_endpoint("/api/v1/queries:run")
        assert "queries" in tool.name
        assert "run" in tool.name
