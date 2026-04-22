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

# cloud_dog_api_kit — MCP HTTP JSON-RPC client transport
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: HTTP JSON-RPC MCP client transport with optional async job
#   polling support.
# Related requirements: FR18.1
# Related architecture: SA1

"""HTTP JSON-RPC MCP client transport."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlsplit, urlunsplit

import httpx

from .base import MCPTransport
from .exceptions import MCPProtocolError, MCPTransportError


@dataclass
class HTTPJSONRPCConfig:
    """Configuration for HTTP JSON-RPC MCP transport."""

    base_url: str
    messages_path: str
    health_path: str
    api_key_header: Optional[str] = None
    api_key: Optional[str] = None
    accept_header: Optional[str] = None
    timeout_seconds: float = 30.0
    verify_tls: bool = True
    async_jobs_enabled: bool = False
    async_jobs_api_base_url: Optional[str] = None
    async_jobs_status_path: str = "/jobs/{job_id}"
    async_jobs_timeout_seconds: float = 120.0
    async_jobs_poll_interval_seconds: float = 2.0
    extra_headers: Optional[Dict[str, str]] = None


class HTTPJSONRPCTransport(MCPTransport):
    """MCP client transport for `/messages` JSON-RPC endpoints."""

    def __init__(self, cfg: HTTPJSONRPCConfig):
        """Initialise HTTPJSONRPCTransport state and dependencies."""
        original_base_url = str(cfg.base_url or "").strip()
        base_url, messages_path = self._normalise_base_and_request_path(
            original_base_url, cfg.messages_path, default_path="/messages"
        )
        _, health_path = self._normalise_base_and_request_path(base_url, cfg.health_path, default_path="/health")
        cfg.base_url = base_url
        cfg.messages_path = messages_path
        cfg.health_path = health_path
        self.cfg = cfg
        self._client: httpx.AsyncClient | None = None
        self._async_jobs_client: httpx.AsyncClient | None = None
        self._id = 0
        self._messages_paths = self._build_messages_paths(
            original_base_url=original_base_url,
            messages_path=messages_path,
        )

    @staticmethod
    def _normalise_base_and_request_path(base_url: str, request_path: str, *, default_path: str) -> tuple[str, str]:
        """Normalise base URL and request path without dropping base path segments."""
        base = str(base_url or "").rstrip("/")
        path = str(request_path or "").strip()
        if not path:
            path = default_path
        if not path.startswith("/"):
            path = f"/{path}"

        parsed = urlsplit(base)
        base_path = (parsed.path or "").rstrip("/")
        if base_path:
            if path == base_path or path.startswith(f"{base_path}/"):
                base = urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
            else:
                path = f"{base_path}{path}"
                base = urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
        return base, path

    @staticmethod
    def _build_messages_paths(*, original_base_url: str, messages_path: str) -> list[str]:
        """Return ordered JSON-RPC endpoint candidates for interop."""
        paths: list[str] = [messages_path]
        parsed = urlsplit(str(original_base_url or "").strip())
        base_path = (parsed.path or "").rstrip("/")
        if base_path and base_path not in paths and messages_path.endswith("/messages"):
            paths.append(base_path)
        return paths

    async def connect(self) -> None:
        """Create the shared transport-owned HTTP client."""
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=str(self.cfg.base_url).rstrip("/"),
            timeout=httpx.Timeout(self.cfg.timeout_seconds, connect=self.cfg.timeout_seconds),
            verify=self.cfg.verify_tls,
            trust_env=True,
        )

    async def close(self) -> None:
        """Close all transport-owned HTTP clients."""
        if self._async_jobs_client is not None:
            await self._async_jobs_client.aclose()
            self._async_jobs_client = None
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        """Build request headers for JSON-RPC calls."""
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
        if self.cfg.accept_header:
            headers["accept"] = self.cfg.accept_header
        return headers

    async def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and return the result object."""
        if self._client is None:
            raise MCPTransportError("Transport not connected")

        self._id += 1
        req_id = self._id
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params

        try:
            resp, request_path = await self._post_jsonrpc(payload)
            if resp.status_code != 200:
                raise MCPTransportError(f"MCP HTTP JSON-RPC failed: POST {request_path} -> {resp.status_code}")
            data = resp.json()
        except httpx.RequestError as exc:
            raise MCPTransportError(
                f"MCP HTTP JSON-RPC request failed: POST {self.cfg.messages_path} -> {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise MCPTransportError(f"MCP HTTP JSON-RPC failed: POST {self.cfg.messages_path} -> {status}") from exc

        if not isinstance(data, dict):
            raise MCPProtocolError("MCP HTTP JSON-RPC returned non-object JSON")
        if data.get("jsonrpc") != "2.0":
            raise MCPProtocolError("MCP HTTP JSON-RPC invalid response: jsonrpc must be '2.0'")
        if data.get("id") != req_id:
            raise MCPProtocolError("MCP HTTP JSON-RPC response id mismatch")
        if data.get("error") is not None:
            raise MCPTransportError(f"MCP HTTP JSON-RPC error: {data['error']}")

        result = data.get("result")
        if not isinstance(result, dict):
            raise MCPProtocolError("MCP HTTP JSON-RPC result must be an object")
        result = await self._maybe_resolve_async_job(method=method, params=params, result=result)
        return result

    async def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification."""
        if self._client is None:
            raise MCPTransportError("Transport not connected")

        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params

        resp, request_path = await self._post_jsonrpc(payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MCPTransportError(f"MCP HTTP JSON-RPC notify failed: POST {request_path} -> {resp.status_code}")

    async def _maybe_resolve_async_job(
        self, *, method: str, params: dict[str, Any] | None, result: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve async job handles when configured for wait=false flows."""
        if not self.cfg.async_jobs_enabled:
            return result
        if method != "tools/call":
            return result
        if not isinstance(params, dict):
            return result
        arguments = params.get("arguments")
        if not isinstance(arguments, dict):
            return result
        if bool(arguments.get("wait", True)):
            return result

        job_ref = self._extract_job_ref(result)
        if not job_ref:
            return result

        job_id = str(job_ref.get("job_id") or "").strip()
        guid = str(job_ref.get("guid") or "").strip()
        if not job_id and not guid:
            return result

        base_url = self._async_jobs_base_url()
        path_template = str(self.cfg.async_jobs_status_path or "/jobs/{job_id}")
        deadline = asyncio.get_running_loop().time() + max(1.0, float(self.cfg.async_jobs_timeout_seconds))
        poll_interval = max(0.1, float(self.cfg.async_jobs_poll_interval_seconds))
        try:
            return await self._poll_async_job(
                base_url=base_url,
                path_template=path_template,
                job_id=job_id,
                guid=guid,
                deadline=deadline,
                poll_interval=poll_interval,
            )
        except MCPTransportError as exc:
            if not self._should_fallback_to_wait_true(exc):
                raise
            try:
                return await self._retry_tools_call_wait_true(params=params)
            except MCPTransportError as retry_exc:
                raise MCPTransportError(f"{exc}; MCP wait=true fallback failed: {retry_exc}") from retry_exc

    async def _ensure_async_jobs_client(self, base_url: str) -> httpx.AsyncClient:
        """Create or reuse the shared async-jobs polling client."""
        if self._async_jobs_client is None:
            poll_timeout = min(30.0, max(1.0, float(self.cfg.timeout_seconds)))
            self._async_jobs_client = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(poll_timeout, connect=poll_timeout),
                verify=self.cfg.verify_tls,
                trust_env=True,
            )
        return self._async_jobs_client

    async def _poll_async_job(
        self,
        *,
        base_url: str,
        path_template: str,
        job_id: str,
        guid: str,
        deadline: float,
        poll_interval: float,
    ) -> dict[str, Any]:
        """Poll async job status endpoint until completion."""
        client = await self._ensure_async_jobs_client(base_url)
        while True:
            path = self._job_status_path(path_template=path_template, job_id=job_id, guid=guid)
            try:
                resp = await client.get(path, headers=self._headers())
            except httpx.RequestError as exc:
                raise MCPTransportError(f"Async job polling request failed: GET {path} -> {exc}") from exc
            if resp.status_code != 200:
                raise MCPTransportError(f"Async job polling failed: GET {path} -> {resp.status_code}")
            try:
                payload = resp.json()
            except Exception as exc:
                raise MCPProtocolError("Async job polling returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise MCPProtocolError("Async job polling returned non-object JSON")

            status = str(payload.get("status") or "").lower()
            if status in {"completed", "failed", "error", "cancelled", "canceled"}:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload, ensure_ascii=True),
                        }
                    ],
                    "isError": status != "completed",
                }

            if asyncio.get_running_loop().time() >= deadline:
                raise MCPTransportError(
                    f"Async job polling timed out after {self.cfg.async_jobs_timeout_seconds}s "
                    f"(job_id={job_id or 'n/a'}, guid={guid or 'n/a'})"
                )
            await asyncio.sleep(poll_interval)

    def _should_fallback_to_wait_true(self, error: MCPTransportError) -> bool:
        """Return True when async status endpoint is not usable."""
        msg = str(error).lower()
        if "async job polling request failed" in msg:
            return True
        return "async job polling failed: get" in msg and "-> 404" in msg

    async def _retry_tools_call_wait_true(self, *, params: dict[str, Any]) -> dict[str, Any]:
        """Retry the same MCP tool call with wait=true using MCP transport only."""
        if self._client is None:
            raise MCPTransportError("Transport not connected")
        retry_params = dict(params)
        arguments = retry_params.get("arguments")
        if not isinstance(arguments, dict):
            raise MCPTransportError("MCP wait=true fallback requires arguments object")
        retry_arguments = dict(arguments)
        retry_arguments["wait"] = True
        retry_params["arguments"] = retry_arguments

        self._id += 1
        req_id = self._id
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": retry_params,
        }
        try:
            resp, request_path = await self._post_jsonrpc(payload)
            if resp.status_code != 200:
                raise MCPTransportError(f"MCP wait=true fallback failed: POST {request_path} -> {resp.status_code}")
            data = resp.json()
        except httpx.RequestError as exc:
            raise MCPTransportError(
                f"MCP wait=true fallback request failed: POST {self.cfg.messages_path} -> {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise MCPProtocolError("MCP wait=true fallback returned non-object JSON")
        if data.get("jsonrpc") != "2.0":
            raise MCPProtocolError("MCP wait=true fallback invalid jsonrpc")
        if data.get("id") != req_id:
            raise MCPProtocolError("MCP wait=true fallback response id mismatch")
        if data.get("error") is not None:
            raise MCPTransportError(f"MCP wait=true fallback error: {data['error']}")
        result = data.get("result")
        if not isinstance(result, dict):
            raise MCPProtocolError("MCP wait=true fallback result must be an object")
        return result

    async def _post_jsonrpc(self, payload: dict[str, Any]) -> tuple[httpx.Response, str]:
        """POST JSON-RPC payload with compatibility fallback paths."""
        if self._client is None:
            raise MCPTransportError("Transport not connected")

        response: httpx.Response | None = None
        request_path = self.cfg.messages_path
        for path in self._messages_paths:
            request_path = path
            response = await self._client.post(path, json=payload, headers=self._headers())
            if response.status_code != 404:
                return response, request_path
        assert response is not None
        return response, request_path

    def _extract_job_ref(self, result: dict[str, Any]) -> dict[str, Any] | None:
        """Extract async job metadata from a tool result payload."""
        if "job_id" in result or "guid" in result:
            return result
        content = result.get("content")
        if not isinstance(content, list):
            return None
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "text":
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            try:
                obj = json.loads(text)
            except Exception:
                continue
            if isinstance(obj, dict) and ("job_id" in obj or "guid" in obj):
                return obj
        return None

    def _async_jobs_base_url(self) -> str:
        """Resolve the async jobs API base URL."""
        explicit = str(self.cfg.async_jobs_api_base_url or "").strip()
        if explicit:
            return explicit.rstrip("/")
        parsed = urlsplit(self.cfg.base_url)
        if parsed.port == 8081:
            netloc = f"{parsed.hostname}:8083" if parsed.hostname else parsed.netloc
            return urlunsplit((parsed.scheme, netloc, "", "", "")).rstrip("/")
        return self.cfg.base_url.rstrip("/")

    def _job_status_path(self, *, path_template: str, job_id: str, guid: str) -> str:
        """Build the job status endpoint path."""
        if "{guid}" in path_template and guid:
            return path_template.format(job_id=job_id or guid, guid=guid)
        return path_template.format(job_id=job_id or guid, guid=guid)
