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

"""UT1.36: MCP transport route registration and mode compatibility."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import socket

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
import uvicorn

from cloud_dog_api_kit.mcp import InMemoryAsyncJobStore, LegacySSEConfig
from cloud_dog_api_kit.mcp.session import SESSION_HEADER
from cloud_dog_api_kit.mcp.transport import register_mcp_routes


async def _echo_tool(payload: dict, _request) -> dict:
    return {"echo": payload}


async def _read_sse_event(line_iter) -> tuple[str | None, str]:
    event_name = None
    data_lines: list[str] = []
    async for line in line_iter:
        if line == "":
            if data_lines:
                return event_name, "\n".join(data_lines)
            event_name = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
    raise AssertionError("SSE stream ended before the next event arrived")


def _read_sse_event_sync(line_iter) -> tuple[str | None, str]:
    event_name = None
    data_lines: list[str] = []
    for line in line_iter:
        if line == "":
            if data_lines:
                return event_name, "\n".join(data_lines)
            event_name = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
    raise AssertionError("SSE stream ended before the next event arrived")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


@contextlib.asynccontextmanager
async def _run_uvicorn(app: FastAPI):
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    task = asyncio.create_task(server.serve())
    try:
        async with AsyncClient() as client:
            base_url = f"http://127.0.0.1:{port}"
            for _ in range(100):
                try:
                    response = await client.get(f"{base_url}/openapi.json")
                    if response.status_code == 200:
                        yield base_url
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            else:
                raise RuntimeError("Timed out waiting for local test server")
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=5)


@pytest.mark.asyncio
class TestMCPTransportHelpers:
    async def test_register_routes_and_call_tool(self) -> None:
        app = FastAPI()
        register_mcp_routes(
            app,
            {"echo": _echo_tool},
            transport_modes={"streamable_http", "http_jsonrpc", "legacy_sse", "stdio"},
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/mcp", json={"tool": "echo", "arguments": {"value": 1}})

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["data"]["echo"]["value"] == 1
        assert response.headers.get(SESSION_HEADER)

    async def test_messages_is_full_jsonrpc_peer_for_initialize_tools_list_and_call(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"http_jsonrpc"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            init = await client.post(
                "/messages",
                json={
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0.1.0"},
                    },
                },
            )
            session_id = init.headers[SESSION_HEADER]
            listed = await client.post(
                "/messages",
                headers={SESSION_HEADER: session_id},
                json={"jsonrpc": "2.0", "id": "list-1", "method": "tools/list"},
            )
            called = await client.post(
                "/messages",
                headers={SESSION_HEADER: session_id},
                json={
                    "jsonrpc": "2.0",
                    "id": "call-1",
                    "method": "tools/call",
                    "params": {"name": "echo", "arguments": {"value": "x"}},
                },
            )

        assert init.status_code == 200
        assert init.json()["result"]["serverInfo"]["name"] == "FastAPI"
        assert listed.status_code == 200
        assert listed.json()["result"]["tools"][0]["name"] == "echo"
        assert called.status_code == 200
        assert json.loads(called.json()["result"]["content"][0]["text"]) == {"echo": {"value": "x"}}

    async def test_initialize_returns_jsonrpc_result_and_session_header(self) -> None:
        app = FastAPI(title="Transport Test", version="1.2.3")
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"streamable_http", "http_jsonrpc"})

        payload = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0.1.0"},
            },
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/mcp", json=payload)

        assert response.status_code == 200
        assert response.headers.get(SESSION_HEADER)
        assert response.json() == {
            "jsonrpc": "2.0",
            "id": "init-1",
            "result": {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "Transport Test", "version": "1.2.3"},
            },
        }

    async def test_notifications_initialized_acknowledged(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"streamable_http"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            init = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0.1.0"},
                    },
                },
            )
            response = await client.post(
                "/mcp",
                headers={SESSION_HEADER: init.headers[SESSION_HEADER]},
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )

        assert response.status_code == 204
        assert response.headers[SESSION_HEADER] == init.headers[SESSION_HEADER]

    async def test_request_context_hook_is_opt_in_and_reaches_three_arg_tool(self) -> None:
        app = FastAPI()
        seen: list[str] = []

        def _hook(request: Request) -> dict:
            seen.append(request.headers.get("x-file-mcp-profile", ""))
            return {"profile": request.headers.get("x-file-mcp-profile"), "source": "hook"}

        async def _context_tool(payload: dict, request: Request, context: dict) -> dict:
            return {
                "echo": payload,
                "profile": context.get("profile"),
                "source": context.get("source"),
                "state_context": getattr(request.state, "mcp_context", {}),
            }

        register_mcp_routes(
            app,
            {"echo": _context_tool},
            transport_modes={"streamable_http"},
            request_context_hook=_hook,
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post(
                "/mcp",
                headers={"X-File-MCP-Profile": "team-a"},
                json={"tool": "echo", "arguments": {"value": 7}},
            )

        assert response.status_code == 200
        assert seen == ["team-a"]
        assert response.json()["data"]["profile"] == "team-a"
        assert response.json()["data"]["source"] == "hook"
        assert response.json()["data"]["state_context"] == {"profile": "team-a", "source": "hook"}

    async def test_default_behaviour_has_no_request_context_hook_side_effects(self) -> None:
        app = FastAPI()

        async def _inspect_tool(payload: dict, request: Request) -> dict:
            return {
                "echo": payload,
                "mcp_context": getattr(request.state, "mcp_context", None),
            }

        register_mcp_routes(app, {"echo": _inspect_tool}, transport_modes={"streamable_http"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/mcp", json={"tool": "echo", "arguments": {"value": 9}})

        assert response.status_code == 200
        assert response.json()["data"]["mcp_context"] is None

    async def test_alternate_endpoints_register_post_get_and_delete_routes(self) -> None:
        app = FastAPI()
        register_mcp_routes(
            app,
            {"echo": _echo_tool},
            transport_modes={"streamable_http", "legacy_sse"},
            alternate_endpoints=[{"path": "/webmcp", "auth": "cookie", "name": "web"}],
        )

        route_map = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes}
        assert ("/webmcp", ("POST",)) in route_map
        assert ("/webmcp", ("GET",)) in route_map
        assert ("/webmcp", ("DELETE",)) in route_map

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            init = await client.post(
                "/webmcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0.1.0"},
                    },
                },
            )
            sse = await client.get("/webmcp")
            deleted = await client.delete("/webmcp", headers={SESSION_HEADER: init.headers[SESSION_HEADER]})

        assert init.status_code == 200
        assert init.headers.get(SESSION_HEADER)
        assert sse.status_code == 200
        assert sse.headers["content-type"].startswith("text/event-stream")
        assert deleted.status_code == 204

    async def test_register_mcp_routes_signature_exposes_new_kwargs(self) -> None:
        signature = inspect.signature(register_mcp_routes)
        assert "request_context_hook" in signature.parameters
        assert "alternate_endpoints" in signature.parameters
        assert "async_job_store" in signature.parameters
        assert "async_job_status_path" in signature.parameters
        assert "legacy_sse" in signature.parameters
        assert "session_termination_mode" in signature.parameters

    async def test_unknown_tool_returns_404_envelope(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"streamable_http"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/mcp", json={"tool": "missing", "arguments": {}})

        assert response.status_code == 404
        assert response.json()["ok"] is False
        assert response.json()["error"]["code"] == "NOT_FOUND"

    async def test_legacy_sse_mode_exposes_event_stream(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"legacy_sse"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.get("/mcp")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

    async def test_async_mode_wait_false_returns_job_and_status_route_completes(self) -> None:
        app = FastAPI()
        started = asyncio.Event()
        allow_finish = asyncio.Event()

        async def _slow_tool(payload: dict, _request: Request) -> dict:
            started.set()
            await allow_finish.wait()
            return {"echo": payload}

        register_mcp_routes(
            app,
            {"echo": _slow_tool},
            transport_modes={"streamable_http"},
            async_job_store=InMemoryAsyncJobStore(),
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            init = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0.1.0"},
                    },
                },
            )
            submit = await client.post(
                "/mcp",
                headers={SESSION_HEADER: init.headers[SESSION_HEADER]},
                json={
                    "jsonrpc": "2.0",
                    "id": "job-1",
                    "method": "tools/call",
                    "params": {"name": "echo", "arguments": {"value": "queued", "wait": False}},
                },
            )
            job_id = submit.json()["result"]["job_id"]
            first_status = await client.get(f"/jobs/{job_id}")
            await asyncio.wait_for(started.wait(), timeout=2)
            running_status = await client.get(f"/jobs/{job_id}")
            allow_finish.set()

            final_status = None
            for _ in range(20):
                polled = await client.get(f"/jobs/{job_id}")
                if polled.json().get("status") == "completed":
                    final_status = polled
                    break
                await asyncio.sleep(0.01)

        assert submit.status_code == 200
        assert submit.json()["result"]["status"] == "pending"
        assert first_status.status_code == 200
        assert first_status.json()["status"] in {"pending", "running"}
        assert running_status.json()["status"] == "running"
        assert final_status is not None
        assert final_status.json()["status"] == "completed"
        assert json.loads(final_status.json()["result"]["content"][0]["text"]) == {"echo": {"value": "queued"}}

    async def test_async_mode_disabled_ignores_wait_false_and_executes_synchronously(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"streamable_http"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            init = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0.1.0"},
                    },
                },
            )
            response = await client.post(
                "/mcp",
                headers={SESSION_HEADER: init.headers[SESSION_HEADER]},
                json={
                    "jsonrpc": "2.0",
                    "id": "call-1",
                    "method": "tools/call",
                    "params": {"name": "echo", "arguments": {"value": "sync", "wait": False}},
                },
            )
            status = await client.get("/jobs/missing-job")

        assert response.status_code == 200
        assert "job_id" not in response.json()["result"]
        assert json.loads(response.json()["result"]["content"][0]["text"]) == {"echo": {"value": "sync"}}
        assert status.status_code == 404

    async def test_legacy_sse_routes_emit_bootstrap_and_correlate_message_responses(self) -> None:
        app = FastAPI()
        register_mcp_routes(
            app,
            {"echo": _echo_tool},
            transport_modes={"streamable_http"},
            legacy_sse=LegacySSEConfig(),
        )

        async with _run_uvicorn(app) as base_url:
            async with AsyncClient(base_url=base_url) as client:
                async with client.stream("GET", "/sse") as response:
                    lines = response.aiter_lines()
                    event_name, raw_data = await _read_sse_event(lines)
                    bootstrap = json.loads(raw_data)
                    session_id = bootstrap["session_id"]

                    post_ack = await client.post(
                        "/message",
                        params={"session_id": session_id},
                        json={"jsonrpc": "2.0", "id": "list-1", "method": "tools/list"},
                    )
                    message_event, message_data = await _read_sse_event(lines)

        assert response.status_code == 200
        assert event_name == "endpoint"
        assert bootstrap["messages_path"] == "/message"
        assert post_ack.status_code == 200
        assert post_ack.json() == {"accepted": True, "session_id": session_id}
        assert message_event == "message"
        assert json.loads(message_data)["result"]["tools"][0]["name"] == "echo"

    async def test_legacy_sse_disabled_by_default_leaves_routes_unregistered(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"streamable_http"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            sse = await client.get("/sse")
            message = await client.post("/message", json={})

        assert sse.status_code == 404
        assert message.status_code == 404

    async def test_session_termination_204_idempotent_mode_stays_default(self) -> None:
        app = FastAPI()
        register_mcp_routes(app, {"echo": _echo_tool}, transport_modes={"streamable_http"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            init = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0.1.0"},
                    },
                },
            )
            deleted = await client.delete("/mcp", headers={SESSION_HEADER: init.headers[SESSION_HEADER]})
            deleted_again = await client.delete("/mcp", headers={SESSION_HEADER: init.headers[SESSION_HEADER]})

        assert deleted.status_code == 204
        assert deleted_again.status_code == 204

    async def test_session_termination_200_json_invalidates_reused_session(self) -> None:
        app = FastAPI()
        register_mcp_routes(
            app,
            {"echo": _echo_tool},
            transport_modes={"streamable_http"},
            session_termination_mode="200_json",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            init = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0.1.0"},
                    },
                },
            )
            session_id = init.headers[SESSION_HEADER]
            deleted = await client.delete("/mcp", headers={SESSION_HEADER: session_id})
            deleted_again = await client.delete("/mcp", headers={SESSION_HEADER: session_id})
            reused = await client.post(
                "/mcp",
                headers={SESSION_HEADER: session_id},
                json={"jsonrpc": "2.0", "id": "list-1", "method": "tools/list"},
            )

        assert deleted.status_code == 200
        assert deleted.json() == {"status": "terminated", "session_id": session_id}
        assert deleted_again.status_code == 404
        assert deleted_again.json() == {"error": "invalid session"}
        assert reused.status_code == 200
        assert reused.json()["error"]["code"] == -32001
