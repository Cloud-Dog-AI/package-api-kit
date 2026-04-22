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

# cloud_dog_api_kit — MCP streamable HTTP client transport
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Streamable HTTP MCP client transport with session reuse, SSE
#   multiplexing, and tool-router compatibility fallbacks.
# Related requirements: FR18.1
# Related architecture: SA1

"""Streamable HTTP MCP client transport."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, cast
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from cloud_dog_api_kit.mcp.session import SESSION_HEADER

from .base import MCPTransport
from .exceptions import MCPProtocolError, MCPSessionError, MCPTransportError


@dataclass
class StreamableHTTPConfig:
    """Configuration for streamable HTTP MCP transport."""

    base_url: str
    mcp_path: str
    api_key_header: Optional[str] = None
    api_key: Optional[str] = None
    accept_header: Optional[str] = None
    sse_accept_header: Optional[str] = None
    protocol_version: Optional[str] = None
    auth_bearer_token: Optional[str] = None
    enable_sse: bool = True
    timeout_seconds: float = 30.0
    read_timeout_seconds: Optional[float] = None
    verify_tls: bool = True
    extra_headers: Optional[Dict[str, str]] = None


class StreamableHTTPTransport(MCPTransport):
    """MCP client transport for the streamable HTTP profile."""

    def __init__(self, cfg: StreamableHTTPConfig):
        """Initialise StreamableHTTPTransport state and dependencies."""
        base_url, mcp_path = self._normalise_base_and_mcp_path(cfg.base_url, cfg.mcp_path)
        cfg.base_url = base_url
        cfg.mcp_path = mcp_path
        self.cfg = cfg
        self._client: httpx.AsyncClient | None = None
        self._id = 0
        self._session_id: str | None = None
        self._sse_task: asyncio.Task[Any] | None = None
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}

    @staticmethod
    def _normalise_base_and_mcp_path(base_url: str, mcp_path: str) -> tuple[str, str]:
        """Normalise base URL and MCP path without doubling path segments."""
        base = str(base_url or "").rstrip("/")
        path = str(mcp_path or "").strip()
        if not path:
            path = "/mcp"
        if not path.startswith("/"):
            path = f"/{path}"

        parsed = urlsplit(base)
        base_path = (parsed.path or "").rstrip("/")
        if base_path and (path == base_path or path.startswith(f"{base_path}/")):
            base = urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
        return base, path

    async def connect(self) -> None:
        """Create the shared transport-owned HTTP client."""
        if self._client is not None:
            return
        read_timeout = self.cfg.read_timeout_seconds
        if read_timeout is not None and read_timeout <= 0:
            read_timeout = None
        elif read_timeout is None:
            read_timeout = self.cfg.timeout_seconds
        self._client = httpx.AsyncClient(
            base_url=str(self.cfg.base_url).rstrip("/"),
            timeout=httpx.Timeout(
                self.cfg.timeout_seconds,
                connect=self.cfg.timeout_seconds,
                read=read_timeout,
            ),
            verify=self.cfg.verify_tls,
            trust_env=True,
        )

    async def close(self) -> None:
        """Cancel the SSE loop, end the server session, and close the HTTP client."""
        if self._sse_task is not None:
            self._sse_task.cancel()
            self._sse_task = None

        if self._client is not None and self._session_id:
            try:
                await self._client.delete(self.cfg.mcp_path, headers=self._headers(include_session=True))
            except Exception:
                pass

        if self._client is not None:
            await self._client.aclose()
            self._client = None

        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(MCPTransportError("Transport closed"))
        self._pending.clear()

    async def terminate_session(self) -> None:
        """Explicitly terminate the current server-side MCP session."""
        if self._client is None or not self._session_id:
            raise MCPSessionError("Transport has no active session to terminate")
        resp = await self._client.delete(self.cfg.mcp_path, headers=self._headers(include_session=True))
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MCPSessionError(f"MCP session terminate failed: DELETE {self.cfg.mcp_path} -> {resp.status_code}")

    async def open_sse_stream(self) -> None:
        """Open the server SSE stream and validate its content type."""
        if self._client is None:
            raise MCPTransportError("Transport not connected")
        async with self._client.stream(
            "GET",
            self.cfg.mcp_path,
            headers=self._sse_headers(),
            timeout=None,
        ) as resp:
            if resp.status_code != 200:
                raise MCPTransportError(f"MCP SSE stream failed: GET {self.cfg.mcp_path} -> {resp.status_code}")
            content_type = (resp.headers.get("content-type") or "").lower()
            if "text/event-stream" not in content_type:
                raise MCPProtocolError("MCP SSE stream missing text/event-stream content type")

    async def ensure_sse_stream(self) -> None:
        """Ensure the background SSE loop is running when enabled."""
        if not self.cfg.enable_sse:
            return
        await self._ensure_sse()

    def _headers(self, *, include_session: bool) -> dict[str, str]:
        """Build standard POST headers for streamable HTTP calls."""
        headers: dict[str, str] = {}
        if isinstance(self.cfg.extra_headers, dict):
            headers.update(
                {
                    str(key): str(value)
                    for key, value in self.cfg.extra_headers.items()
                    if str(key).strip() and str(value).strip()
                }
            )
        if self.cfg.api_key_header and self.cfg.api_key:
            headers[self.cfg.api_key_header] = self.cfg.api_key
        if self.cfg.auth_bearer_token:
            headers["authorization"] = f"Bearer {self.cfg.auth_bearer_token}"
        if self.cfg.accept_header:
            headers["accept"] = self.cfg.accept_header
        if self.cfg.protocol_version:
            headers["mcp-protocol-version"] = self.cfg.protocol_version
        if include_session and self._session_id:
            headers[SESSION_HEADER] = self._session_id
        return headers

    def _sse_headers(self) -> dict[str, str]:
        """Build SSE request headers for streamable HTTP."""
        headers: dict[str, str] = {}
        if isinstance(self.cfg.extra_headers, dict):
            headers.update(
                {
                    str(key): str(value)
                    for key, value in self.cfg.extra_headers.items()
                    if str(key).strip() and str(value).strip()
                }
            )
        if self.cfg.api_key_header and self.cfg.api_key:
            headers[self.cfg.api_key_header] = self.cfg.api_key
        if self.cfg.auth_bearer_token:
            headers["authorization"] = f"Bearer {self.cfg.auth_bearer_token}"
        accept_value = self.cfg.sse_accept_header or self.cfg.accept_header
        if accept_value:
            headers["accept"] = accept_value
        if self.cfg.protocol_version:
            headers["mcp-protocol-version"] = self.cfg.protocol_version
        if self._session_id:
            headers[SESSION_HEADER] = self._session_id
        return headers

    async def _ensure_sse(self) -> None:
        """Start the background SSE loop once a session exists."""
        if self._sse_task is not None:
            return
        if self._client is None:
            raise MCPTransportError("Transport not connected")
        if not self._session_id:
            raise MCPSessionError("Cannot open SSE stream without session id")
        self._sse_task = asyncio.create_task(self._sse_loop())

    async def _sse_loop(self) -> None:
        """Consume background SSE frames and resolve pending requests."""
        assert self._client is not None
        assert self._session_id

        try:
            async with self._client.stream(
                "GET",
                self.cfg.mcp_path,
                headers=self._sse_headers(),
                timeout=None,
            ) as resp:
                if resp.status_code != 200:
                    raise MCPTransportError(f"MCP SSE stream failed: GET {self.cfg.mcp_path} -> {resp.status_code}")

                event_data: list[str] = []
                async for line in resp.aiter_lines():
                    if line is None:
                        continue
                    if line == "":
                        if event_data:
                            raw = "\n".join(event_data)
                            event_data = []
                            try:
                                message = json.loads(raw)
                            except Exception:
                                continue
                            self._handle_incoming(message)
                        continue
                    if line.startswith(":"):
                        continue
                    if line.startswith("id:"):
                        continue
                    if line.startswith("data:"):
                        event_data.append(line[5:].lstrip())
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(MCPTransportError(f"SSE stream failed: {exc}"))
            self._pending.clear()

    def _handle_incoming(self, message: Any) -> None:
        """Handle background server-to-client JSON-RPC messages."""
        if not isinstance(message, dict):
            return
        if message.get("jsonrpc") != "2.0":
            return

        if "method" in message and message.get("id") is not None:
            method = str(message.get("method") or "")
            req_id = message.get("id")
            if method in ("sampling/createMessage", "elicitation/create"):
                error = {"code": -32601, "message": f"Client does not support {method}"}
            else:
                error = {
                    "code": -32601,
                    "message": f"Client does not support method {method}",
                }
            response = {"jsonrpc": "2.0", "id": req_id, "error": error}
            asyncio.create_task(self._send_client_response(response))
            return

        if "id" in message and message.get("id") is not None:
            req_id = message.get("id")
            if isinstance(req_id, int) and req_id in self._pending:
                future = self._pending.pop(req_id)
                if message.get("error") is not None:
                    future.set_exception(MCPTransportError(f"MCP error: {message['error']}"))
                    return

                result = message.get("result")
                if not isinstance(result, dict):
                    future.set_exception(MCPProtocolError("MCP result must be an object"))
                    return

                future.set_result(result)

    async def _send_client_response(self, response: dict[str, Any]) -> None:
        """Reply to server-initiated requests with method-not-found errors."""
        if self._client is None:
            return
        try:
            await self._client.post(
                self.cfg.mcp_path,
                json=response,
                headers=self._headers(include_session=True),
            )
        except Exception:
            return

    def _parse_inline_sse(self, text: Any) -> list[dict[str, Any]]:
        """Parse inline SSE payloads returned in a single HTTP response body."""
        if isinstance(text, bytes):
            text = text.decode(errors="replace")
        if not isinstance(text, str):
            return []

        messages: list[dict[str, Any]] = []
        event_data: list[str] = []
        for line in text.splitlines():
            if line == "":
                if event_data:
                    raw = "\n".join(event_data)
                    event_data = []
                    try:
                        message = json.loads(raw)
                    except Exception:
                        continue
                    if isinstance(message, dict):
                        messages.append(message)
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                event_data.append(line[5:].lstrip())
        if event_data:
            raw = "\n".join(event_data)
            try:
                message = json.loads(raw)
            except Exception:
                return messages
            if isinstance(message, dict):
                messages.append(message)
        return messages

    def _tool_router_base_path(self) -> str:
        """Return the tool-router prefix paired with the MCP base path."""
        base = self.cfg.mcp_path.rstrip("/")
        if not base:
            base = "/mcp"
        return f"{base}/tools"

    @staticmethod
    def _normalise_tools_list_payload(payload: Any) -> dict[str, Any]:
        """Normalise tool-router style tools/list payloads."""
        if isinstance(payload, list):
            return {"tools": payload}
        if isinstance(payload, dict):
            tools = payload.get("tools")
            if isinstance(tools, list):
                return {"tools": tools}
            data = payload.get("data")
            if isinstance(data, list):
                return {"tools": data}
            result = payload.get("result")
            if isinstance(result, dict):
                result_tools = result.get("tools")
                if isinstance(result_tools, list):
                    return {"tools": result_tools}
                result_items = result.get("items")
                if isinstance(result_items, list):
                    return {"tools": result_items}
        raise MCPTransportError("MCP tool-router tools/list response missing tools payload")

    @staticmethod
    def _normalise_tools_call_payload(payload: Any) -> dict[str, Any]:
        """Normalise tool-router style tools/call payloads."""
        if isinstance(payload, dict) and isinstance(payload.get("content"), list):
            return payload

        is_error = False
        data: Any = payload
        if isinstance(payload, dict):
            is_error = bool(payload.get("isError") is True) or bool(payload.get("ok") is False)
            if payload.get("data") is not None:
                data = payload.get("data")
            elif payload.get("result") is not None:
                data = payload.get("result")

        text = json.dumps(data, ensure_ascii=True)
        return {"content": [{"type": "text", "text": text}], "isError": is_error}

    @staticmethod
    def _is_bare_result_method(method: str) -> bool:
        """Return True when a bare dict payload is a valid result object."""
        return method in {
            "prompts/list",
            "prompts/get",
            "resources/list",
            "resources/read",
            "resources/templates/list",
        }

    async def _request_tool_router_fallback(self, *, method: str, params: dict[str, Any] | None) -> dict[str, Any]:
        """Fallback to REST-style tool-router endpoints when needed."""
        if self._client is None:
            raise MCPTransportError("Transport not connected")

        headers = self._headers(include_session=bool(self._session_id))
        tools_path = self._tool_router_base_path()

        async def _request_with_retry(
            http_method: str, endpoint: str, *, json_body: dict[str, Any] | None = None
        ) -> httpx.Response:
            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    if http_method == "GET":
                        return await self._client.get(endpoint, headers=headers)
                    return await self._client.post(endpoint, json=json_body, headers=headers)
                except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                    last_error = exc
                    if attempt < 2:
                        await asyncio.sleep(0.25 * (attempt + 1))
                        continue
                    raise MCPTransportError(
                        f"MCP tool-router fallback transport failed for {http_method} {endpoint}: {exc}"
                    ) from exc
            raise MCPTransportError(
                f"MCP tool-router fallback transport failed for {http_method} {endpoint}: {last_error}"
            )

        if method == "tools/list":
            list_endpoints = [tools_path, "/api/v1/tools"]
            for endpoint in list_endpoints:
                resp = await _request_with_retry("GET", endpoint)
                if resp.status_code in {404, 405}:
                    continue
                if resp.status_code != 200:
                    raise MCPTransportError(f"MCP tool-router fallback failed: GET {endpoint} -> {resp.status_code}")
                try:
                    payload = resp.json()
                except Exception as exc:
                    raise MCPProtocolError(
                        f"MCP tool-router tools/list returned non-JSON payload from {endpoint}"
                    ) from exc
                return self._normalise_tools_list_payload(payload)

            raise MCPTransportError(f"MCP tool-router fallback has no tools/list endpoint under {tools_path}")

        if method == "tools/call":
            if not isinstance(params, dict):
                raise MCPTransportError("MCP tool-router fallback requires object params for tools/call")
            name = str(params.get("name") or "").strip()
            if not name:
                raise MCPTransportError("MCP tool-router fallback requires params.name for tools/call")
            arguments = params.get("arguments")
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, dict):
                raise MCPTransportError("MCP tool-router fallback requires params.arguments object for tools/call")

            call_endpoints = [
                (f"{tools_path}/{quote(name, safe='')}", arguments),
                (f"/api/v1/tools/{quote(name, safe='')}", arguments),
            ]
            last_error: str | None = None
            for endpoint, body in call_endpoints:
                resp = await _request_with_retry("POST", endpoint, json_body=body)
                if resp.status_code in {404, 405, 500}:
                    last_error = f"MCP tool-router fallback failed: POST {endpoint} -> {resp.status_code}"
                    continue
                if resp.status_code != 200:
                    raise MCPTransportError(f"MCP tool-router fallback failed: POST {endpoint} -> {resp.status_code}")
                try:
                    payload = resp.json()
                except Exception as exc:
                    raise MCPProtocolError(
                        f"MCP tool-router tools/call ({name}) returned non-JSON payload from {endpoint}"
                    ) from exc
                return self._normalise_tools_call_payload(payload)

            if last_error:
                raise MCPTransportError(last_error)
            raise MCPTransportError(f"MCP tool-router fallback has no tools/call endpoint for '{name}'")

        raise MCPTransportError(f"MCP tool-router fallback unsupported for method '{method}'")

    async def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send one MCP request over the streamable HTTP transport."""
        if self._client is None:
            raise MCPTransportError("Transport not connected")

        self._id += 1
        req_id = self._id
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params

        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future

        async def _send_once() -> str | dict[str, Any]:
            headers = self._headers(include_session=bool(self._session_id))
            async with self._client.stream("POST", self.cfg.mcp_path, json=payload, headers=headers) as resp:
                if resp.status_code < 200 or resp.status_code >= 300:
                    self._pending.pop(req_id, None)
                    body_bytes = await resp.aread()
                    body = (body_bytes.decode(errors="replace") or "").strip()
                    if len(body) > 500:
                        body = body[:500] + "...<truncated>"
                    if method in {"tools/list", "tools/call"} and resp.status_code in {404, 405, 501}:
                        return await self._request_tool_router_fallback(method=method, params=params)
                    raise MCPTransportError(
                        f"MCP Streamable HTTP failed: POST {self.cfg.mcp_path} -> {resp.status_code}; body={body}"
                    )

                session_id = resp.headers.get(SESSION_HEADER)
                if session_id and not self._session_id:
                    self._session_id = session_id
                    if self.cfg.enable_sse:
                        await self._ensure_sse()

                content_type = (resp.headers.get("content-type") or "").lower()
                if "text/event-stream" in content_type:
                    event_data: list[str] = []
                    async for line in resp.aiter_lines():
                        if line == "":
                            if event_data:
                                raw = "\n".join(event_data)
                                event_data = []
                                try:
                                    message = json.loads(raw)
                                except Exception:
                                    continue
                                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                                    continue
                                if message.get("id") != req_id:
                                    continue
                                if message.get("error") is not None:
                                    self._pending.pop(req_id, None)
                                    raise MCPTransportError(f"MCP error: {message['error']}")
                                result = message.get("result")
                                if not isinstance(result, dict):
                                    self._pending.pop(req_id, None)
                                    raise MCPProtocolError("MCP result must be an object")
                                self._pending.pop(req_id, None)
                                return result
                            continue

                        if line.startswith(":"):
                            continue
                        if line.startswith("data:"):
                            event_data.append(line[5:].lstrip())
                            continue

                    if event_data:
                        raw = "\n".join(event_data)
                        try:
                            message = json.loads(raw)
                        except Exception:
                            message = None
                        if (
                            isinstance(message, dict)
                            and message.get("jsonrpc") == "2.0"
                            and message.get("id") == req_id
                        ):
                            if message.get("error") is not None:
                                self._pending.pop(req_id, None)
                                raise MCPTransportError(f"MCP error: {message['error']}")
                            result = message.get("result")
                            if not isinstance(result, dict):
                                self._pending.pop(req_id, None)
                                raise MCPProtocolError("MCP result must be an object")
                            self._pending.pop(req_id, None)
                            return result
                    raise MCPTransportError("MCP SSE response did not include a matching result")

                body_bytes = await resp.aread()
                return body_bytes.decode(errors="replace").strip()

        body_or_result: str | dict[str, Any] = ""
        for attempt in range(3):
            try:
                body_or_result = await _send_once()
                break
            except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                if attempt < 2:
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                if method in {"tools/list", "tools/call"}:
                    try:
                        return await self._request_tool_router_fallback(method=method, params=params)
                    except MCPTransportError:
                        pass
                self._pending.pop(req_id, None)
                raise MCPTransportError(f"MCP Streamable HTTP transport failed: {exc}") from exc

        data: Any = None
        if isinstance(body_or_result, dict):
            data = body_or_result
            body_text = json.dumps(body_or_result, ensure_ascii=True)
        else:
            body_text = body_or_result
            try:
                data = json.loads(body_text) if body_text else None
            except Exception:
                data = None

        if isinstance(data, dict) and data.get("jsonrpc") == "2.0" and data.get("id") == req_id:
            if data.get("error") is not None:
                error = data.get("error")
                if (
                    method in {"tools/list", "tools/call"}
                    and isinstance(error, dict)
                    and int(error.get("code") or 0) == -32601
                ):
                    return await self._request_tool_router_fallback(method=method, params=params)
                self._pending.pop(req_id, None)
                raise MCPTransportError(f"MCP error: {error}")

            result = data.get("result")
            if not isinstance(result, dict):
                self._pending.pop(req_id, None)
                raise MCPProtocolError("MCP result must be an object")

            self._pending.pop(req_id, None)
            return result

        if method == "initialize" and isinstance(data, dict):
            if data.get("protocolVersion") is not None or data.get("serverInfo") is not None:
                self._pending.pop(req_id, None)
                return data

        if self._is_bare_result_method(method) and isinstance(data, dict):
            self._pending.pop(req_id, None)
            return data

        if method == "tools/list" and data is not None:
            try:
                result = self._normalise_tools_list_payload(data)
                self._pending.pop(req_id, None)
                return result
            except MCPTransportError:
                pass

        if method == "tools/call" and data is not None:
            try:
                result = self._normalise_tools_call_payload(data)
                self._pending.pop(req_id, None)
                return result
            except MCPTransportError:
                pass

        if body_text:
            for message in self._parse_inline_sse(body_text):
                if message.get("jsonrpc") == "2.0" and message.get("id") == req_id:
                    if message.get("error") is not None:
                        self._pending.pop(req_id, None)
                        raise MCPTransportError(f"MCP error: {message['error']}")
                    result = message.get("result")
                    if not isinstance(result, dict):
                        self._pending.pop(req_id, None)
                        raise MCPProtocolError("MCP result must be an object")
                    self._pending.pop(req_id, None)
                    return result

        try:
            result = await asyncio.wait_for(future, timeout=self.cfg.timeout_seconds)
            return cast(dict[str, Any], result)
        except asyncio.TimeoutError as exc:
            if method in {"tools/list", "tools/call"}:
                try:
                    return await self._request_tool_router_fallback(method=method, params=params)
                except MCPTransportError:
                    pass

            detail = {
                "session_id": self._session_id,
                "body": body_text[:500] + ("...<truncated>" if len(body_text) > 500 else ""),
            }
            raise MCPTransportError(f"MCP Streamable HTTP timeout waiting for response: {detail}") from exc
        finally:
            self._pending.pop(req_id, None)

    async def initialize(
        self,
        *,
        protocol_version: str,
        client_name: str = "cloud-dog-chat-client",
        client_version: str = "0.1.0",
    ) -> None:
        """Perform initialisation with interop-tolerant fallbacks."""
        if not protocol_version:
            raise MCPTransportError("MCP initialize requires protocol_version")
        try:
            await self.request(
                "initialize",
                params={
                    "protocolVersion": protocol_version,
                    "clientInfo": {"name": client_name, "version": client_version},
                    "capabilities": {},
                },
            )
        except MCPTransportError as exc:
            message = str(exc)
            if self._is_nonfatal_initialize_failure(message):
                return
            raise
        try:
            await self.notify("notifications/initialized")
        except MCPTransportError as exc:
            message = str(exc)
            if "Streamable HTTP notifications require an established session" in message:
                return
            raise

    @staticmethod
    def _is_nonfatal_initialize_failure(message: str) -> bool:
        """Return True when initialise rejection is interop-tolerable."""
        text = str(message or "").lower()
        if (
            "mcp streamable http failed" in text
            and "post " in text
            and ("-> 404" in text or "-> 405" in text or "-> 501" in text)
        ):
            return True
        if "mcp error" in text and ("-32601" in text or "method not found" in text):
            return True
        return False

    async def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a notification over the established streamable HTTP session."""
        if self._client is None:
            raise MCPTransportError("Transport not connected")
        if not self._session_id:
            raise MCPSessionError("Streamable HTTP notifications require an established session")

        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params

        resp = await self._client.post(self.cfg.mcp_path, json=payload, headers=self._headers(include_session=True))
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MCPTransportError(
                f"MCP Streamable HTTP notify failed: POST {self.cfg.mcp_path} -> {resp.status_code}"
            )
