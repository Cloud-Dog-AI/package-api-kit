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

# cloud_dog_api_kit — MCP tool router
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tool registry router for typed MCP tool calls and metadata.
# Related requirements: FR18.1
# Related architecture: SA1

"""MCP tool router helpers."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from cloud_dog_api_kit.envelopes import error_envelope, success_envelope
from cloud_dog_api_kit.errors import APIError
from cloud_dog_api_kit.mcp.error_mapper import map_legacy_mcp_payload

ToolCallable = Callable[[dict[str, Any], Request], Awaitable[Any] | Any]
ToolRegistryType = dict[str, "ToolContract | ToolCallable | dict[str, Any]"]


@dataclass(slots=True)
class ToolContract:
    """Contract for a tool exposed via MCP transport."""

    name: str
    handler: ToolCallable
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)


def normalise_tool_registry(tool_registry: ToolRegistryType | None) -> dict[str, ToolContract]:
    """Normalise different registry value shapes into ToolContract values."""
    contracts: dict[str, ToolContract] = {}
    for name, value in (tool_registry or {}).items():
        if isinstance(value, ToolContract):
            contracts[name] = value
            continue
        if callable(value):
            contracts[name] = ToolContract(name=name, handler=value)
            continue
        if isinstance(value, dict) and callable(value.get("handler")):
            contracts[name] = ToolContract(
                name=name,
                handler=value["handler"],
                description=str(value.get("description", "")),
                input_schema=dict(value.get("input_schema") or {}),
                output_schema=dict(value.get("output_schema") or {}),
            )
            continue
        raise TypeError(f"Unsupported tool registry entry for {name!r}")
    return contracts


async def _invoke_tool(contract: ToolContract, payload: dict[str, Any], request: Request) -> Any:
    """Invoke tool handler with best-effort signature compatibility."""
    parameter_count = len(inspect.signature(contract.handler).parameters)
    if parameter_count <= 1:
        result = contract.handler(payload)  # type: ignore[call-arg]
    else:
        result = contract.handler(payload, request)
    if inspect.isawaitable(result):
        return await result
    return result


def register_tool_router(
    app: FastAPI,
    tool_registry: ToolRegistryType | None,
    *,
    base_path: str = "/mcp/tools",
) -> dict[str, ToolContract]:
    """Register MCP tool routes on a FastAPI app."""
    contracts = normalise_tool_registry(tool_registry)

    @app.get(base_path, tags=["mcp"])
    async def list_tools() -> dict[str, Any]:
        """List tools."""
        return success_envelope(
            data=[
                {
                    "name": contract.name,
                    "description": contract.description,
                    "input_schema": contract.input_schema,
                    "output_schema": contract.output_schema,
                }
                for contract in contracts.values()
            ],
        )

    @app.post(f"{base_path}/{{tool_name}}", tags=["mcp"])
    async def call_tool(tool_name: str, request: Request) -> JSONResponse:
        """Handle call tool."""
        request_id = getattr(request.state, "request_id", "")
        correlation_id = getattr(request.state, "correlation_id", None)
        contract = contracts.get(tool_name)
        if contract is None:
            return JSONResponse(
                status_code=404,
                content=error_envelope(
                    code="NOT_FOUND",
                    message=f"Unknown MCP tool: {tool_name}",
                    request_id=request_id,
                    correlation_id=correlation_id,
                ),
            )
        payload = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        try:
            result = await _invoke_tool(contract, payload, request)
        except APIError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content=error_envelope(
                    code=exc.code,
                    message=exc.message,
                    details=exc.details,
                    retryable=exc.retryable,
                    request_id=request_id,
                    correlation_id=correlation_id,
                ),
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content=error_envelope(
                    code="INTERNAL_ERROR",
                    message="Tool execution failed",
                    request_id=request_id,
                    correlation_id=correlation_id,
                ),
            )

        mapped = map_legacy_mcp_payload(result, request_id=request_id, correlation_id=correlation_id)
        status_code = 200 if mapped.get("ok", True) else 400
        return JSONResponse(status_code=status_code, content=mapped)

    return contracts
