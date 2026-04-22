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

# cloud_dog_api_kit — MCP legacy SSE client transport
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Legacy SSE MCP client transport for endpoint-discovery servers.
# Related requirements: FR18.1
# Related architecture: SA1

"""Legacy SSE MCP client transport."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

import httpx

from cloud_dog_api_kit.mcp.session import SESSION_HEADER

from .base import MCPTransport
from .exceptions import MCPProtocolError, MCPTransportError


@dataclass
class LegacySSEConfig:
    """Configuration for legacy SSE MCP transport."""

    base_url: str
    sse_path: str
    messages_path: str
    api_key_header: Optional[str] = None
    api_key: Optional[str] = None
    accept_header: Optional[str] = None
    auth_bearer_token: Optional[str] = None
    protocol_version: Optional[str] = None
    timeout_seconds: float = 30.0
    verify_tls: bool = True


class LegacySSETransport(MCPTransport):
    """MCP client transport for legacy SSE + message-post servers."""

    def __init__(self, cfg: LegacySSEConfig):
        """Initialise LegacySSETransport state and dependencies."""
        self.cfg = cfg
        self._client: httpx.AsyncClient | None = None
        self._sse_task: asyncio.Task[Any] | None = None
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._id = 0
        self._message_endpoint: str | None = None
        self._session_id: str | None = None
        self._endpoint_ready = asyncio.Event()

    async def connect(self) -> None:
        """Create the shared HTTP client and start the SSE loop."""
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=str(self.cfg.base_url).rstrip("/"),
            timeout=httpx.Timeout(self.cfg.timeout_seconds, connect=self.cfg.timeout_seconds),
            verify=self.cfg.verify_tls,
            trust_env=True,
        )
        await self._ensure_sse()

    async def close(self) -> None:
        """Close the SSE loop, HTTP client, and pending requests."""
        if self._sse_task is not None:
            self._sse_task.cancel()
            self._sse_task = None
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(MCPTransportError("Transport closed"))
        self._pending.clear()

    async def _ensure_sse(self) -> None:
        """Start the background SSE reader once."""
        if self._sse_task is not None:
            return
        if self._client is None:
            raise MCPTransportError("Transport not connected")
        self._sse_task = asyncio.create_task(self._sse_loop())

    def _headers(self) -> dict[str, str]:
        """Build standard JSON request headers."""
        headers: dict[str, str] = {"accept": "application/json"}
        if self.cfg.accept_header:
            headers["accept"] = self.cfg.accept_header
        if self.cfg.api_key_header and self.cfg.api_key:
            headers[self.cfg.api_key_header] = self.cfg.api_key
        if self.cfg.auth_bearer_token:
            headers["authorization"] = f"Bearer {self.cfg.auth_bearer_token}"
        if self.cfg.protocol_version:
            headers["mcp-protocol-version"] = self.cfg.protocol_version
        return headers

    def _sse_headers(self) -> dict[str, str]:
        """Build SSE request headers."""
        headers: dict[str, str] = {"accept": "text/event-stream"}
        if self.cfg.api_key_header and self.cfg.api_key:
            headers[self.cfg.api_key_header] = self.cfg.api_key
        if self.cfg.auth_bearer_token:
            headers["authorization"] = f"Bearer {self.cfg.auth_bearer_token}"
        if self.cfg.protocol_version:
            headers["mcp-protocol-version"] = self.cfg.protocol_version
        return headers

    def _set_endpoint(self, endpoint: str) -> None:
        """Capture the messages endpoint announced via SSE."""
        endpoint = endpoint.strip()
        parsed = urlparse(endpoint)
        if parsed.scheme and parsed.netloc:
            self._message_endpoint = endpoint
            query = parse_qs(parsed.query)
        else:
            if not endpoint.startswith("/"):
                endpoint = f"/{endpoint}"
            self._message_endpoint = endpoint
            query = parse_qs(urlparse(endpoint).query)
        session_id = query.get("sessionId", []) or query.get("session_id", [])
        if session_id:
            self._session_id = session_id[0]
        self._endpoint_ready.set()

    def _endpoint_with_session(self, endpoint: str) -> str:
        """Append session_id query param when required for compatibility."""
        if not self._session_id:
            return endpoint
        parsed = urlparse(endpoint)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if "session_id" in query or "sessionId" in query:
            return endpoint
        query["session_id"] = self._session_id
        rebuilt = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
        if parsed.scheme and parsed.netloc:
            return rebuilt
        if not rebuilt.startswith("/"):
            return f"/{rebuilt}"
        return rebuilt

    def _message_headers(self, endpoint: str) -> dict[str, str]:
        """Build POST headers for legacy message endpoint calls."""
        headers = self._headers()
        if self._session_id:
            has_session_header = any(str(key).lower() == SESSION_HEADER.lower() for key in headers)
            if not has_session_header:
                headers[SESSION_HEADER] = self._session_id
        return headers

    async def _wait_for_endpoint(self) -> None:
        """Wait for the server to announce the message endpoint."""
        if self._message_endpoint:
            return
        try:
            await asyncio.wait_for(self._endpoint_ready.wait(), timeout=self.cfg.timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise MCPTransportError("Timed out waiting for legacy SSE endpoint") from exc
        if not self._message_endpoint:
            raise MCPTransportError("Legacy SSE endpoint not provided by server")

    async def _sse_loop(self) -> None:
        """Consume legacy SSE events and dispatch JSON-RPC replies."""
        assert self._client is not None
        event_name: str | None = None
        data_lines: list[str] = []

        try:
            async with self._client.stream("GET", self.cfg.sse_path, headers=self._sse_headers(), timeout=None) as resp:
                if resp.status_code < 200 or resp.status_code >= 300:
                    raise MCPTransportError(f"Legacy SSE GET failed: {resp.status_code}")
                content_type = (resp.headers.get("content-type") or "").lower()
                if "text/event-stream" not in content_type:
                    raise MCPProtocolError("Legacy SSE stream missing text/event-stream content type")

                async for line in resp.aiter_lines():
                    if line == "":
                        if not data_lines:
                            continue
                        data_text = "\n".join(data_lines)
                        self._handle_event(event_name, data_text)
                        event_name = None
                        data_lines = []
                        continue
                    if line.startswith(":"):
                        continue
                    if line.startswith("event:"):
                        event_name = line[len("event:") :].strip()
                        continue
                    if line.startswith("data:"):
                        data_lines.append(line[len("data:") :].lstrip())
        except asyncio.CancelledError:
            return

    def _handle_event(self, event_name: str | None, data_text: str) -> None:
        """Handle legacy SSE endpoint and message events."""
        if event_name == "endpoint":
            try:
                payload = json.loads(data_text)
                if isinstance(payload, dict):
                    session_id = payload.get("session_id") or payload.get("sessionId")
                    if session_id:
                        self._session_id = str(session_id)
                    endpoint = payload.get("endpoint") or payload.get("path") or payload.get("messages_path") or ""
                    if endpoint:
                        self._set_endpoint(str(endpoint))
                        return
            except Exception:
                pass
            self._set_endpoint(data_text)
            return

        try:
            payload = json.loads(data_text)
        except Exception:
            return

        if isinstance(payload, dict) and payload.get("jsonrpc") == "2.0":
            msg_id = payload.get("id")
            if msg_id is not None and msg_id in self._pending:
                future = self._pending.pop(msg_id)
                if not future.done():
                    future.set_result(payload)

    def _extract_result(self, payload: Any, *, req_id: int) -> dict[str, Any]:
        """Validate a JSON-RPC response payload and return the result object."""
        if not isinstance(payload, dict):
            raise MCPProtocolError("Legacy SSE response returned non-object JSON")
        if payload.get("jsonrpc") != "2.0":
            raise MCPProtocolError("Legacy SSE invalid response: jsonrpc must be '2.0'")
        if payload.get("id") != req_id:
            raise MCPProtocolError("Legacy SSE response id mismatch")
        if payload.get("error") is not None:
            raise MCPTransportError(f"Legacy SSE JSON-RPC error: {payload['error']}")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise MCPProtocolError("Legacy SSE result must be an object")
        return result

    async def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request via legacy message POST + SSE response."""
        await self.connect()
        await self._wait_for_endpoint()
        assert self._client is not None
        self._id += 1
        req_id = self._id
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future

        endpoint = self._endpoint_with_session(self._message_endpoint or self.cfg.messages_path)
        resp = await self._client.post(endpoint, json=payload, headers=self._message_headers(endpoint))
        if resp.status_code < 200 or resp.status_code >= 300:
            self._pending.pop(req_id, None)
            raise MCPTransportError(f"Legacy SSE message POST failed: {resp.status_code}")

        try:
            direct_result = resp.json()
        except Exception:
            direct_result = None
        if isinstance(direct_result, dict) and direct_result.get("jsonrpc") == "2.0":
            self._pending.pop(req_id, None)
            if not future.done():
                future.cancel()
            result = self._extract_result(direct_result, req_id=req_id)
            return {
                **result,
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }

        try:
            result = await asyncio.wait_for(future, timeout=self.cfg.timeout_seconds)
        except asyncio.TimeoutError as exc:
            self._pending.pop(req_id, None)
            if not future.done():
                future.cancel()
            raise MCPTransportError("Timed out waiting for legacy SSE response event") from exc
        extracted = self._extract_result(result, req_id=req_id)
        return {
            **extracted,
            "jsonrpc": "2.0",
            "id": req_id,
            "result": extracted,
        }

    async def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification via the legacy message endpoint."""
        await self.connect()
        await self._wait_for_endpoint()
        assert self._client is not None
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        endpoint = self._endpoint_with_session(self._message_endpoint or self.cfg.messages_path)
        resp = await self._client.post(endpoint, json=payload, headers=self._message_headers(endpoint))
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MCPTransportError(f"Legacy SSE notify failed: {resp.status_code}")
