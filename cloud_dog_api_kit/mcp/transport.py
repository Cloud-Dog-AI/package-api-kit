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

# cloud_dog_api_kit — MCP transport helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Route registration helpers for MCP transport compatibility
#   modes and tool dispatch.
# Related requirements: FR18.1
# Related architecture: SA1

"""MCP transport route registration helpers."""

from __future__ import annotations

import inspect
import json
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from cloud_dog_api_kit.envelopes import error_envelope, success_envelope
from cloud_dog_api_kit.mcp.error_mapper import map_legacy_mcp_payload
from cloud_dog_api_kit.mcp.session import SESSION_HEADER, McpSessionManager
from cloud_dog_api_kit.mcp.tool_router import ToolContract, normalise_tool_registry

TransportModes = set[str]
ToolCallable = Callable[[dict[str, Any], Request], Awaitable[Any] | Any]

SUPPORTED_TRANSPORT_MODES = frozenset({"streamable_http", "http_jsonrpc", "legacy_sse", "stdio"})


def _normalise_transport_modes(transport_modes: list[str] | set[str] | tuple[str, ...] | None) -> TransportModes:
    modes = set(transport_modes or SUPPORTED_TRANSPORT_MODES)
    unknown = modes - SUPPORTED_TRANSPORT_MODES
    if unknown:
        unknown_str = ", ".join(sorted(unknown))
        raise ValueError(f"Unsupported transport mode(s): {unknown_str}")
    return modes


async def _call_tool(tool: ToolContract, payload: dict[str, Any], request: Request) -> Any:
    parameter_count = len(inspect.signature(tool.handler).parameters)
    if parameter_count <= 1:
        result = tool.handler(payload)  # type: ignore[call-arg]
    else:
        result = tool.handler(payload, request)
    if inspect.isawaitable(result):
        return await result
    return result


async def _dispatch_payload(
    tools: dict[str, ToolContract],
    payload: dict[str, Any],
    request: Request,
) -> tuple[int, dict[str, Any]]:
    request_id = getattr(request.state, "request_id", "")
    correlation_id = getattr(request.state, "correlation_id", None)

    # JSON-RPC shape
    if payload.get("jsonrpc") == "2.0":
        method = str(payload.get("method", ""))
        params = dict(payload.get("params") or {})
        if method == "tools/list":
            result = success_envelope(
                data=[
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                        "output_schema": tool.output_schema,
                    }
                    for tool in tools.values()
                ],
                request_id=request_id,
                correlation_id=correlation_id,
            )
            return 200, result
        if method != "tools/call":
            return (
                400,
                error_envelope(
                    code="INVALID_REQUEST",
                    message=f"Unsupported JSON-RPC method: {method}",
                    request_id=request_id,
                    correlation_id=correlation_id,
                ),
            )
        tool_name = str(params.get("name", ""))
        arguments = dict(params.get("arguments") or {})
    else:
        tool_name = str(payload.get("tool", payload.get("name", "")))
        arguments = dict(payload.get("arguments") or payload.get("input") or {})

    tool = tools.get(tool_name)
    if tool is None:
        return (
            404,
            error_envelope(
                code="NOT_FOUND",
                message=f"Unknown MCP tool: {tool_name}",
                request_id=request_id,
                correlation_id=correlation_id,
            ),
        )

    result = await _call_tool(tool, arguments, request)
    mapped = map_legacy_mcp_payload(result, request_id=request_id, correlation_id=correlation_id)
    status = 200 if mapped.get("ok", True) else 400
    return status, mapped


def register_mcp_routes(
    app: FastAPI,
    tools: dict[str, ToolContract | ToolCallable | dict[str, Any]] | None,
    transport_modes: list[str] | set[str] | tuple[str, ...] | None = None,
    *,
    session_manager: McpSessionManager | None = None,
) -> McpSessionManager:
    """Register MCP compatibility routes.

    Registers:
    - `POST /mcp` for streamable HTTP and JSON-RPC payloads
    - `POST /messages` legacy alias for MCP calls
    - `GET /mcp` SSE compatibility stream (legacy mode)
    """
    enabled_modes = _normalise_transport_modes(transport_modes)
    tool_registry = normalise_tool_registry(tools)
    manager = session_manager or McpSessionManager()

    app.state.mcp_transport_modes = sorted(enabled_modes)
    app.state.mcp_session_manager = manager

    async def _handle_mcp(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

        existing_session_id = request.headers.get(SESSION_HEADER)
        session, created = manager.ensure(existing_session_id)
        status, body = await _dispatch_payload(tool_registry, payload, request)
        response = JSONResponse(status_code=status, content=body)
        response.headers[SESSION_HEADER] = session.session_id
        response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
        return response

    @app.post("/mcp", tags=["mcp"])
    async def mcp_transport(request: Request) -> JSONResponse:
        """Handle mcp transport."""
        return await _handle_mcp(request)

    @app.post("/messages", tags=["mcp"])
    async def mcp_messages(request: Request) -> JSONResponse:
        """Handle mcp messages."""
        return await _handle_mcp(request)

    @app.get("/mcp", tags=["mcp"], response_model=None)
    async def mcp_legacy_sse() -> Response:
        """Handle mcp legacy sse."""
        if "legacy_sse" not in enabled_modes:
            return JSONResponse(status_code=404, content=error_envelope(code="NOT_FOUND", message="Route not enabled"))

        async def _event_stream() -> Any:
            payload = {
                "type": "ready",
                "modes": sorted(enabled_modes),
                "tools": sorted(tool_registry.keys()),
            }
            yield f"event: ready\ndata: {json.dumps(payload)}\n\n"

        return StreamingResponse(_event_stream(), media_type="text/event-stream")

    return manager
