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
from typing import Any, Awaitable, Callable, Literal

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from cloud_dog_api_kit.envelopes import error_envelope, success_envelope
from cloud_dog_api_kit.mcp.async_jobs import AsyncJobStore
from cloud_dog_api_kit.mcp.error_mapper import map_legacy_mcp_payload
from cloud_dog_api_kit.mcp.legacy_sse import LegacySSEBroker, LegacySSEConfig
from cloud_dog_api_kit.mcp.session import SESSION_HEADER, McpSessionManager
from cloud_dog_api_kit.mcp.tool_router import ToolContract, normalise_tool_registry

TransportModes = set[str]
ToolCallable = Callable[[dict[str, Any], Request], Awaitable[Any] | Any]
RequestContextHook = Callable[[Request], dict[str, Any] | None]
SessionTerminationMode = Literal["204_idempotent", "200_json"]

SUPPORTED_TRANSPORT_MODES = frozenset({"streamable_http", "http_jsonrpc", "legacy_sse", "stdio"})


def _normalise_transport_modes(transport_modes: list[str] | set[str] | tuple[str, ...] | None) -> TransportModes:
    modes = set(transport_modes or SUPPORTED_TRANSPORT_MODES)
    unknown = modes - SUPPORTED_TRANSPORT_MODES
    if unknown:
        unknown_str = ", ".join(sorted(unknown))
        raise ValueError(f"Unsupported transport mode(s): {unknown_str}")
    return modes


def _jsonrpc_response(
    request_id: Any,
    *,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = dict(result or {})
    return response


def _mcp_initialize_payload(
    *,
    protocol_version: str,
    server_name: str,
    server_version: str,
) -> dict[str, Any]:
    negotiated = str(protocol_version or "").strip() or "2025-11-25"
    return {
        "protocolVersion": negotiated,
        "capabilities": {
            "tools": {},
            "resources": {},
        },
        "serverInfo": {
            "name": server_name,
            "version": server_version,
        },
    }


def _mcp_tools_list_payload(tools: dict[str, ToolContract]) -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "outputSchema": tool.output_schema,
            }
            for tool in tools.values()
        ]
    }


def _mcp_tool_call_payload(result: Any) -> dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("content"), list):
        return result
    if isinstance(result, list) and all(isinstance(item, dict) and "type" in item for item in result):
        return {"content": result}

    is_error = False
    data: Any = result
    if isinstance(result, dict):
        if result.get("ok") is False:
            is_error = True
        if result.get("data") is not None:
            data = result.get("data")
        elif result.get("result") is not None:
            data = result.get("result")
        elif result.get("error") is not None:
            is_error = True
            data = result.get("error")

    if isinstance(data, str):
        text = data
    else:
        text = json.dumps(data, default=str, ensure_ascii=True)
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _messages_compat_payload(
    *,
    jsonrpc_payload: dict[str, Any],
    legacy_result: Any | None,
    request_id: Any,
    correlation_id: Any,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach legacy envelope fields to `/messages` JSON-RPC responses."""
    payload = dict(jsonrpc_payload)
    if error is not None:
        payload["ok"] = False
        payload["error"] = {"code": error.get("code"), "message": error.get("message")}
        return payload

    mapped = map_legacy_mcp_payload(legacy_result, request_id=request_id, correlation_id=correlation_id)
    payload["ok"] = mapped.get("ok", True)
    if "data" in mapped:
        payload["data"] = mapped["data"]
    if "error" in mapped:
        payload["error"] = mapped["error"]
    return payload


async def _call_tool(
    tool: ToolContract,
    payload: dict[str, Any],
    request: Request,
    tool_context: dict[str, Any],
) -> Any:
    parameter_count = len(inspect.signature(tool.handler).parameters)
    if parameter_count <= 1:
        result = tool.handler(payload)  # type: ignore[call-arg]
    elif parameter_count == 2:
        result = tool.handler(payload, request)
    else:
        result = tool.handler(payload, request, tool_context)  # type: ignore[call-arg]
    if inspect.isawaitable(result):
        return await result
    return result


def _normalise_alternate_endpoints(
    alternate_endpoints: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    normalised: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for index, entry in enumerate(alternate_endpoints or []):
        if not isinstance(entry, dict):
            raise TypeError("alternate_endpoints entries must be dictionaries")
        raw_path = str(entry.get("path") or "").strip()
        if not raw_path:
            raise ValueError("alternate_endpoints entries require a non-empty path")
        path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
        if path in seen_paths:
            continue
        seen_paths.add(path)
        auth_mode = str(entry.get("auth") or "custom").strip() or "custom"
        name = str(entry.get("name") or f"alternate-{index + 1}").strip() or f"alternate-{index + 1}"
        normalised.append({"path": path, "auth": auth_mode, "name": name})
    return normalised


async def _resolve_tool_context(
    request: Request,
    *,
    request_context_hook: RequestContextHook | None,
) -> dict[str, Any]:
    base_context = getattr(request.state, "mcp_context", None)
    has_context = isinstance(base_context, dict)
    context = dict(base_context) if has_context else {}
    if request_context_hook is not None:
        hook_result = request_context_hook(request)
        if inspect.isawaitable(hook_result):
            hook_result = await hook_result
        if hook_result is not None:
            if not isinstance(hook_result, dict):
                raise TypeError("request_context_hook must return a dict or None")
            context.update(hook_result)
            has_context = True
    if has_context:
        request.state.mcp_context = context
    return context


async def _dispatch_payload(
    tools: dict[str, ToolContract],
    payload: dict[str, Any],
    request: Request,
    *,
    session_manager: McpSessionManager,
    request_context_hook: RequestContextHook | None,
    async_job_store: AsyncJobStore | None,
    modern_jsonrpc: bool,
    server_name: str,
    server_version: str,
    invalid_session_ids: set[str],
    session_id_override: str | None = None,
) -> Response:
    request_id = getattr(request.state, "request_id", "")
    correlation_id = getattr(request.state, "correlation_id", None)
    is_messages_path = request.url.path.endswith("/messages")
    session_id = (
        session_id_override
        or request.headers.get(SESSION_HEADER)
        or request.query_params.get("session_id")
        or request.query_params.get("sessionId")
    )
    if session_id and session_id in invalid_session_ids and not session_manager.exists(session_id):
        if payload.get("jsonrpc") == "2.0" and modern_jsonrpc:
            error_payload = {"code": -32001, "message": "Invalid or expired MCP session"}
            response_payload = _jsonrpc_response(
                payload.get("id"),
                error=error_payload,
            )
            if is_messages_path:
                response_payload = _messages_compat_payload(
                    jsonrpc_payload=response_payload,
                    legacy_result=None,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    error=error_payload,
                )
            response = JSONResponse(
                status_code=200,
                content=response_payload,
            )
            response.headers[SESSION_HEADER] = session_id
            return response
        response = JSONResponse(
            status_code=404,
            content=error_envelope(
                code="INVALID_SESSION",
                message="Invalid or expired MCP session",
                request_id=request_id,
                correlation_id=correlation_id,
            ),
        )
        response.headers[SESSION_HEADER] = session_id
        return response

    session, created = session_manager.ensure(session_id)
    invalid_session_ids.discard(session.session_id)

    # JSON-RPC shape
    if payload.get("jsonrpc") == "2.0":
        method = str(payload.get("method", ""))
        params = dict(payload.get("params") or {})
        rpc_request_id = payload.get("id")
        if modern_jsonrpc:
            if method == "initialize":
                protocol_version = str(params.get("protocolVersion") or "2025-11-25").strip()
                session.metadata["protocol_version"] = protocol_version
                init_payload = _mcp_initialize_payload(
                    protocol_version=protocol_version,
                    server_name=server_name,
                    server_version=server_version,
                )
                response_payload = _jsonrpc_response(
                    rpc_request_id,
                    result=init_payload,
                )
                if is_messages_path:
                    response_payload = _messages_compat_payload(
                        jsonrpc_payload=response_payload,
                        legacy_result=init_payload,
                        request_id=request_id,
                        correlation_id=correlation_id,
                    )
                response = JSONResponse(
                    status_code=200,
                    content=response_payload,
                )
                response.headers[SESSION_HEADER] = session.session_id
                response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
                return response
            if method == "notifications/initialized":
                session.metadata["initialized"] = True
                response = Response(status_code=204, media_type="application/json")
                response.headers[SESSION_HEADER] = session.session_id
                response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
                return response
            if method == "tools/list":
                tools_payload = _mcp_tools_list_payload(tools)
                response_payload = _jsonrpc_response(
                    rpc_request_id,
                    result=tools_payload,
                )
                if is_messages_path:
                    response_payload = _messages_compat_payload(
                        jsonrpc_payload=response_payload,
                        legacy_result=tools_payload,
                        request_id=request_id,
                        correlation_id=correlation_id,
                    )
                response = JSONResponse(
                    status_code=200,
                    content=response_payload,
                )
                response.headers[SESSION_HEADER] = session.session_id
                response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
                return response
            if method == "ping":
                ping_payload = {"ok": True}
                response_payload = _jsonrpc_response(
                    rpc_request_id,
                    result=ping_payload,
                )
                if is_messages_path:
                    response_payload = _messages_compat_payload(
                        jsonrpc_payload=response_payload,
                        legacy_result=ping_payload,
                        request_id=request_id,
                        correlation_id=correlation_id,
                    )
                response = JSONResponse(
                    status_code=200,
                    content=response_payload,
                )
                response.headers[SESSION_HEADER] = session.session_id
                response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
                return response
            if method != "tools/call":
                error_payload = {"code": -32601, "message": f"Unsupported JSON-RPC method: {method}"}
                response_payload = _jsonrpc_response(
                    rpc_request_id,
                    error=error_payload,
                )
                if is_messages_path:
                    response_payload = _messages_compat_payload(
                        jsonrpc_payload=response_payload,
                        legacy_result=None,
                        request_id=request_id,
                        correlation_id=correlation_id,
                        error=error_payload,
                    )
                response = JSONResponse(
                    status_code=200,
                    content=response_payload,
                )
                response.headers[SESSION_HEADER] = session.session_id
                response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
                return response
        if method == "tools/list":
            response = JSONResponse(
                status_code=200,
                content=success_envelope(
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
                ),
            )
            response.headers[SESSION_HEADER] = session.session_id
            response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
            return response
        if method != "tools/call":
            response = JSONResponse(
                status_code=400,
                content=error_envelope(
                    code="INVALID_REQUEST",
                    message=f"Unsupported JSON-RPC method: {method}",
                    request_id=request_id,
                    correlation_id=correlation_id,
                ),
            )
            response.headers[SESSION_HEADER] = session.session_id
            response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
            return response
        tool_name = str(params.get("name", ""))
        arguments = dict(params.get("arguments") or {})
        wait_value = params.get("wait")
        if "wait" in arguments:
            wait_value = arguments.pop("wait")
    else:
        tool_name = str(payload.get("tool", payload.get("name", "")))
        arguments = dict(payload.get("arguments") or payload.get("input") or {})
        wait_value = payload.get("wait")
        if "wait" in arguments:
            wait_value = arguments.pop("wait")

    tool = tools.get(tool_name)
    if tool is None:
        response = JSONResponse(
            status_code=404,
            content=error_envelope(
                code="NOT_FOUND",
                message=f"Unknown MCP tool: {tool_name}",
                request_id=request_id,
                correlation_id=correlation_id,
            ),
        )
        response.headers[SESSION_HEADER] = session.session_id
        response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
        return response

    tool_context = await _resolve_tool_context(request, request_context_hook=request_context_hook)
    if payload.get("jsonrpc") == "2.0" and modern_jsonrpc and async_job_store is not None and wait_value is False:
        async def _runner() -> Any:
            return await _call_tool(tool, arguments, request, tool_context)

        job_id = await _maybe_await(
            async_job_store.submit(
                tool_name,
                arguments,
                {
                    "request": request,
                    "session_id": session.session_id,
                    "tool_context": tool_context,
                    "runner": _runner,
                    "result_formatter": _mcp_tool_call_payload,
                },
            )
        )
        job_payload = {"job_id": job_id, "status": "pending"}
        response_payload = _jsonrpc_response(payload.get("id"), result=job_payload)
        if is_messages_path:
            response_payload = _messages_compat_payload(
                jsonrpc_payload=response_payload,
                legacy_result=job_payload,
                request_id=request_id,
                correlation_id=correlation_id,
            )
        response = JSONResponse(
            status_code=200,
            content=response_payload,
        )
        response.headers[SESSION_HEADER] = session.session_id
        response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
        return response

    result = await _call_tool(tool, arguments, request, tool_context)
    if payload.get("jsonrpc") == "2.0" and modern_jsonrpc:
        tool_payload = _mcp_tool_call_payload(result)
        response_payload = _jsonrpc_response(payload.get("id"), result=tool_payload)
        if is_messages_path:
            response_payload = _messages_compat_payload(
                jsonrpc_payload=response_payload,
                legacy_result=result,
                request_id=request_id,
                correlation_id=correlation_id,
            )
        response = JSONResponse(
            status_code=200,
            content=response_payload,
        )
        response.headers[SESSION_HEADER] = session.session_id
        response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
        return response
    mapped = map_legacy_mcp_payload(result, request_id=request_id, correlation_id=correlation_id)
    status = 200 if mapped.get("ok", True) else 400
    response = JSONResponse(status_code=status, content=mapped)
    response.headers[SESSION_HEADER] = session.session_id
    response.headers["X-Mcp-Session-Created"] = "true" if created else "false"
    return response


def register_mcp_routes(
    app: FastAPI,
    tools: dict[str, ToolContract | ToolCallable | dict[str, Any]] | None,
    transport_modes: list[str] | set[str] | tuple[str, ...] | None = None,
    *,
    session_manager: McpSessionManager | None = None,
    request_context_hook: RequestContextHook | None = None,
    alternate_endpoints: list[dict[str, Any]] | None = None,
    async_job_store: AsyncJobStore | None = None,
    async_job_status_path: str | None = "/jobs/{job_id}",
    legacy_sse: LegacySSEConfig | None = None,
    session_termination_mode: SessionTerminationMode = "204_idempotent",
) -> McpSessionManager:
    """Register MCP compatibility routes.

    Registers:
    - `POST /mcp` for streamable HTTP and JSON-RPC payloads
    - `POST /messages` legacy alias for MCP calls
    - `GET /mcp` SSE compatibility stream (legacy mode)
    - `DELETE /mcp` session termination for streamable HTTP clients

    Keyword-only options:
    - `request_context_hook`: optional per-request hook that returns a context
      dict merged into `request.state.mcp_context` and passed to 3-argument tool
      handlers as `(payload, request, context)`.
    - `alternate_endpoints`: optional additional MCP route families, e.g.
      `[{"path": "/webmcp", "auth": "cookie", "name": "web"}]`.
    - `async_job_store`: optional async wait=false job store for JSON-RPC
      `tools/call` requests.
    - `async_job_status_path`: optional GET route for async job status polling.
    - `legacy_sse`: optional `/sse` + `/message` compatibility transport config.
    - `session_termination_mode`: choose the default `204` idempotent delete
      behaviour or the expert-agent-compatible `200` JSON variant.
    """
    enabled_modes = _normalise_transport_modes(transport_modes)
    tool_registry = normalise_tool_registry(tools)
    manager = session_manager or McpSessionManager()
    alternate_routes = _normalise_alternate_endpoints(alternate_endpoints)
    server_name = str(getattr(app, "title", "") or "mcp-server").strip() or "mcp-server"
    server_version = str(getattr(app, "version", "") or "0.0.0").strip() or "0.0.0"
    invalid_session_ids: set[str] = set()
    legacy_sse_config = legacy_sse
    legacy_sse_broker = LegacySSEBroker(legacy_sse_config) if legacy_sse_config is not None else None

    app.state.mcp_transport_modes = sorted(enabled_modes)
    app.state.mcp_session_manager = manager

    async def _handle_mcp(
        request: Request,
        *,
        modern_jsonrpc: bool,
        session_id_override: str | None = None,
    ) -> Response:
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

        return await _dispatch_payload(
            tool_registry,
            payload,
            request,
            session_manager=manager,
            request_context_hook=request_context_hook,
            async_job_store=async_job_store,
            modern_jsonrpc=modern_jsonrpc,
            server_name=server_name,
            server_version=server_version,
            invalid_session_ids=invalid_session_ids,
            session_id_override=session_id_override,
        )

    async def _handle_delete(request: Request) -> Response:
        session_id = request.headers.get(SESSION_HEADER)
        if session_termination_mode == "204_idempotent":
            if session_id:
                manager.delete(session_id)
                invalid_session_ids.discard(session_id)
            return Response(status_code=204)

        if not session_id or not manager.delete(session_id):
            return JSONResponse(status_code=404, content={"error": "invalid session"})
        invalid_session_ids.add(session_id)
        return JSONResponse(status_code=200, content={"status": "terminated", "session_id": session_id})

    @app.post("/mcp", tags=["mcp"])
    async def mcp_transport(request: Request) -> Response:
        """Handle mcp transport."""
        return await _handle_mcp(request, modern_jsonrpc=True)

    @app.post("/messages", tags=["mcp"])
    async def mcp_messages(request: Request) -> Response:
        """Handle mcp messages."""
        return await _handle_mcp(request, modern_jsonrpc=True)

    @app.delete("/mcp", tags=["mcp"])
    async def mcp_transport_delete(request: Request) -> Response:
        """Terminate an MCP session if present."""
        return await _handle_delete(request)

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

    if async_job_store is not None and async_job_status_path:
        async def mcp_async_job_status(job_id: str) -> Response:
            """Return the current async MCP tool-call job status."""
            status = await _maybe_await(async_job_store.get_status(job_id))
            if not isinstance(status, dict):
                return JSONResponse(status_code=500, content={"error": "invalid async job status payload"})
            if status.get("status") == "not_found":
                return JSONResponse(status_code=404, content={"error": status.get("error", "Job not found")})
            return JSONResponse(status_code=200, content=status)

        app.add_api_route(
            async_job_status_path,
            mcp_async_job_status,
            methods=["GET"],
            tags=["mcp"],
            name="mcp_async_job_status",
        )

    if legacy_sse_config is not None and legacy_sse_broker is not None:
        @app.get(legacy_sse_config.sse_path, tags=["mcp"], response_model=None)
        async def legacy_sse_stream(request: Request) -> Response:
            """Handle legacy SSE compatibility bootstrap and message delivery."""
            session_id = request.headers.get(legacy_sse_config.session_header)
            session, _created = manager.ensure(session_id)
            invalid_session_ids.discard(session.session_id)
            return StreamingResponse(
                legacy_sse_broker.event_stream(request, session.session_id),
                media_type="text/event-stream",
            )

        @app.post(legacy_sse_config.message_path, tags=["mcp"])
        async def legacy_sse_message(request: Request) -> Response:
            """Accept a legacy SSE-correlated JSON-RPC POST and push the reply to the stream."""
            resolved_session = (
                request.query_params.get("session_id")
                or request.query_params.get("sessionId")
                or request.headers.get(legacy_sse_config.session_header)
            )
            if not resolved_session:
                return JSONResponse(status_code=400, content={"error": "missing session_id"})

            response = await _handle_mcp(
                request,
                modern_jsonrpc=True,
                session_id_override=resolved_session,
            )
            if response.status_code != 204 and getattr(response, "body", b""):
                try:
                    payload = json.loads(response.body.decode("utf-8"))
                except Exception:
                    payload = {"error": "invalid response payload"}
                await legacy_sse_broker.push(resolved_session, payload)
            return JSONResponse(status_code=200, content={"accepted": True, "session_id": resolved_session})

    for route in alternate_routes:
        route_path = route["path"]
        tags = ["mcp", f"mcp:{route['auth']}"]

        async def _alternate_post(request: Request, *, _modern: bool = True) -> Response:
            return await _handle_mcp(request, modern_jsonrpc=_modern)

        async def _alternate_delete(request: Request) -> Response:
            return await _handle_delete(request)

        async def _alternate_get() -> Response:
            if "legacy_sse" not in enabled_modes:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope(code="NOT_FOUND", message="Route not enabled"),
                )

            async def _event_stream() -> Any:
                payload = {
                    "type": "ready",
                    "modes": sorted(enabled_modes),
                    "tools": sorted(tool_registry.keys()),
                }
                yield f"event: ready\ndata: {json.dumps(payload)}\n\n"

            return StreamingResponse(_event_stream(), media_type="text/event-stream")

        app.add_api_route(
            route_path,
            _alternate_post,
            methods=["POST"],
            tags=tags,
            name=f"mcp_transport_{route['name']}",
        )
        app.add_api_route(
            route_path,
            _alternate_get,
            methods=["GET"],
            tags=tags,
            response_model=None,
            name=f"mcp_transport_sse_{route['name']}",
        )
        app.add_api_route(
            route_path,
            _alternate_delete,
            methods=["DELETE"],
            tags=tags,
            name=f"mcp_transport_delete_{route['name']}",
        )

    return manager
