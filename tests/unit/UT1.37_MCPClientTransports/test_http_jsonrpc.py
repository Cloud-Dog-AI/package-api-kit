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

"""UT1.37 HTTP JSON-RPC MCP transport coverage."""

from __future__ import annotations

import json

import httpx
import pytest

from cloud_dog_api_kit.mcp.client_transport import (
    HTTPJSONRPCConfig,
    HTTPJSONRPCTransport,
    MCPTransportError,
)


@pytest.mark.asyncio
class TestHTTPJSONRPCTransport:
    async def test_wait_false_polls_job_until_completed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        counters = {"job_get": 0}
        real_async_client = httpx.AsyncClient

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path == "/messages":
                body = json.loads(request.content.decode("utf-8"))
                assert body["method"] == "tools/call"
                assert body["params"]["arguments"]["wait"] is False
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {"job_id": "JOB-UT-1", "guid": "GUID-UT-1"},
                                        ensure_ascii=True,
                                    ),
                                }
                            ]
                        },
                    },
                )

            if request.method == "GET" and request.url.path == "/jobs/JOB-UT-1":
                counters["job_get"] += 1
                if counters["job_get"] == 1:
                    return httpx.Response(200, json={"job_id": "JOB-UT-1", "status": "running"})
                return httpx.Response(
                    200,
                    json={"job_id": "JOB-UT-1", "status": "completed", "result": {"answer": "ok"}},
                )

            raise AssertionError(f"Unexpected request: {request.method} {request.url}")

        created_clients: list[str] = []

        def client_factory(*args, **kwargs):
            base_url = str(kwargs.get("base_url") or "")
            created_clients.append(base_url)
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(*args, **kwargs)

        monkeypatch.setattr(
            "cloud_dog_api_kit.mcp.client_transport.http_jsonrpc.httpx.AsyncClient",
            client_factory,
        )

        transport = HTTPJSONRPCTransport(
            HTTPJSONRPCConfig(
                base_url="http://mcp.example:8081",
                messages_path="/messages",
                health_path="/health",
                timeout_seconds=5,
                verify_tls=True,
                async_jobs_enabled=True,
                async_jobs_api_base_url="http://mcp.example:8083",
                async_jobs_status_path="/jobs/{job_id}",
                async_jobs_timeout_seconds=10,
                async_jobs_poll_interval_seconds=0.01,
            )
        )

        await transport.connect()
        try:
            assert transport._client is not None
            assert transport._client.trust_env is True
            result = await transport.request(
                "tools/call",
                params={"name": "query_database", "arguments": {"question": "x", "wait": False}},
            )
            assert transport._async_jobs_client is not None
            assert transport._async_jobs_client.trust_env is True
        finally:
            await transport.close()

        assert counters["job_get"] >= 2
        assert created_clients.count("http://mcp.example:8081") == 1
        assert created_clients.count("http://mcp.example:8083") == 1
        content = result.get("content") or []
        assert isinstance(content, list) and content
        payload = json.loads(content[0]["text"])
        assert payload["status"] == "completed"
        assert payload["job_id"] == "JOB-UT-1"
        assert result.get("isError") is False

    async def test_wait_false_poll_timeout_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real_async_client = httpx.AsyncClient

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path == "/messages":
                body = json.loads(request.content.decode("utf-8"))
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {"job_id": "JOB-UT-TIMEOUT", "guid": "GUID-UT-TIMEOUT"},
                                        ensure_ascii=True,
                                    ),
                                }
                            ]
                        },
                    },
                )

            if request.method == "GET" and request.url.path == "/jobs/JOB-UT-TIMEOUT":
                return httpx.Response(200, json={"job_id": "JOB-UT-TIMEOUT", "status": "running"})

            raise AssertionError(f"Unexpected request: {request.method} {request.url}")

        def client_factory(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(*args, **kwargs)

        monkeypatch.setattr(
            "cloud_dog_api_kit.mcp.client_transport.http_jsonrpc.httpx.AsyncClient",
            client_factory,
        )

        transport = HTTPJSONRPCTransport(
            HTTPJSONRPCConfig(
                base_url="http://mcp.example:8081",
                messages_path="/messages",
                health_path="/health",
                timeout_seconds=5,
                verify_tls=True,
                async_jobs_enabled=True,
                async_jobs_api_base_url="http://mcp.example:8083",
                async_jobs_status_path="/jobs/{job_id}",
                async_jobs_timeout_seconds=0.03,
                async_jobs_poll_interval_seconds=0.01,
            )
        )

        await transport.connect()
        try:
            with pytest.raises(MCPTransportError) as exc_info:
                await transport.request(
                    "tools/call",
                    params={"name": "query_database", "arguments": {"question": "x", "wait": False}},
                )
        finally:
            await transport.close()

        assert "Async job polling timed out" in str(exc_info.value)

    async def test_poll_404_falls_back_to_wait_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        counters = {"post_wait_false": 0, "post_wait_true": 0, "job_get": 0}
        real_async_client = httpx.AsyncClient

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and request.url.path == "/messages":
                body = json.loads(request.content.decode("utf-8"))
                wait_value = bool(body.get("params", {}).get("arguments", {}).get("wait", True))
                if not wait_value:
                    counters["post_wait_false"] += 1
                    return httpx.Response(
                        200,
                        json={
                            "jsonrpc": "2.0",
                            "id": body["id"],
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(
                                            {"job_id": "JOB-UT-FALLBACK", "guid": "GUID-UT-FALLBACK"},
                                            ensure_ascii=True,
                                        ),
                                    }
                                ]
                            },
                        },
                    )
                counters["post_wait_true"] += 1
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {"content": [{"type": "text", "text": "Japan China corruption comparison summary"}]},
                    },
                )

            if request.method == "GET" and request.url.path == "/jobs/JOB-UT-FALLBACK":
                counters["job_get"] += 1
                return httpx.Response(404, json={"detail": "Not Found"})

            raise AssertionError(f"Unexpected request: {request.method} {request.url}")

        def client_factory(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(*args, **kwargs)

        monkeypatch.setattr(
            "cloud_dog_api_kit.mcp.client_transport.http_jsonrpc.httpx.AsyncClient",
            client_factory,
        )

        transport = HTTPJSONRPCTransport(
            HTTPJSONRPCConfig(
                base_url="http://mcp.example:8081",
                messages_path="/messages",
                health_path="/health",
                timeout_seconds=5,
                verify_tls=True,
                async_jobs_enabled=True,
                async_jobs_api_base_url="http://mcp.example:8083",
                async_jobs_status_path="/jobs/{job_id}",
                async_jobs_timeout_seconds=10,
                async_jobs_poll_interval_seconds=0.01,
            )
        )

        await transport.connect()
        try:
            result = await transport.request(
                "tools/call",
                params={"name": "query_database", "arguments": {"question": "x", "wait": False}},
            )
        finally:
            await transport.close()

        assert counters["post_wait_false"] == 1
        assert counters["job_get"] == 1
        assert counters["post_wait_true"] == 1
        assert result["content"][0]["text"] == "Japan China corruption comparison summary"
