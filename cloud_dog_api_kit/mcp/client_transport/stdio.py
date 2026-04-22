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

# cloud_dog_api_kit — MCP stdio client transport
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Stdio-based MCP client transport with content-length and
#   newline framing support.
# Related requirements: FR18.1
# Related architecture: SA1

"""Stdio MCP client transport."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import MCPTransport
from .exceptions import MCPProtocolError, MCPTransportError


@dataclass
class StdioConfig:
    """Configuration for stdio MCP transport."""

    command: str
    args: list[str]
    env: Optional[Dict[str, str]] = None
    framing: str = "content_length"


class StdioTransport(MCPTransport):
    """MCP client transport that talks to subprocess stdio."""

    def __init__(self, cfg: StdioConfig):
        """Initialise StdioTransport state and dependencies."""
        self.cfg = cfg
        self._proc: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[Any] | None = None
        self._stderr_task: asyncio.Task[Any] | None = None
        self._wait_task: asyncio.Task[Any] | None = None
        self._stderr_buf = bytearray()
        self._line_buf = bytearray()
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._id = 0

    async def connect(self) -> None:
        """Start the subprocess and background readers."""
        if self._proc is not None:
            return

        env = None
        if self.cfg.env is not None:
            env = {str(key): str(value) for key, value in self.cfg.env.items()}

        self._proc = await asyncio.create_subprocess_exec(
            self.cfg.command,
            *self.cfg.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        if self._proc.stdin is None or self._proc.stdout is None:
            raise MCPTransportError("Failed to open stdio pipes")

        self._reader_task = asyncio.create_task(self._read_loop())
        if self._proc.stderr is not None:
            self._stderr_task = asyncio.create_task(self._drain_stderr())
        self._wait_task = asyncio.create_task(self._wait_for_exit())

    async def close(self) -> None:
        """Shut down the subprocess and fail pending requests."""
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None

        if self._stderr_task is not None:
            self._stderr_task.cancel()
            self._stderr_task = None

        if self._wait_task is not None:
            self._wait_task.cancel()
            self._wait_task = None

        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
            except Exception:
                pass

            try:
                self._proc.terminate()
            except Exception:
                pass

            try:
                await asyncio.wait_for(self._proc.wait(), timeout=2.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(MCPTransportError("Transport closed"))
        self._pending.clear()

    def _stderr_tail(self, *, limit: int = 4096) -> str:
        """Return a safe tail of captured stderr."""
        if not self._stderr_buf:
            return ""
        tail = bytes(self._stderr_buf[-limit:])
        return tail.decode("utf-8", errors="replace")

    async def _drain_stderr(self) -> None:
        """Continuously capture stderr for diagnostics."""
        assert self._proc is not None
        assert self._proc.stderr is not None

        while True:
            chunk = await self._proc.stderr.read(4096)
            if not chunk:
                return
            self._stderr_buf.extend(chunk)
            if len(self._stderr_buf) > 200_000:
                del self._stderr_buf[:100_000]

    async def _wait_for_exit(self) -> None:
        """Fail pending requests if the subprocess exits unexpectedly."""
        assert self._proc is not None
        return_code = await self._proc.wait()
        message = f"STDIO process exited with code {return_code}"
        tail = self._stderr_tail()
        if tail:
            message = message + f"; stderr tail: {tail.strip()}"
        error = MCPTransportError(message)
        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(error)
        self._pending.clear()

    async def _read_exactly(self, size: int) -> bytes:
        """Read exactly the requested number of bytes from stdout."""
        assert self._proc is not None
        assert self._proc.stdout is not None
        try:
            return await self._proc.stdout.readexactly(size)
        except asyncio.IncompleteReadError as exc:
            raise MCPTransportError("STDIO server closed stdout") from exc

    async def _read_message(self) -> dict[str, Any]:
        """Read one JSON-RPC message using configured framing."""
        assert self._proc is not None
        assert self._proc.stdout is not None

        if str(self.cfg.framing).lower().strip() in ("newline", "ndjson", "jsonl"):
            while True:
                if b"\n" not in self._line_buf:
                    chunk = await self._proc.stdout.read(4096)
                    if not chunk:
                        raise MCPTransportError("STDIO server closed stdout")
                    self._line_buf.extend(chunk)
                    continue
                line_bytes, _, remainder = self._line_buf.partition(b"\n")
                self._line_buf = bytearray(remainder)
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except Exception as exc:
                    raise MCPProtocolError("Failed to parse newline-delimited STDIO JSON message") from exc
                if not isinstance(message, dict):
                    raise MCPProtocolError("STDIO message must be a JSON object")
                return message

        content_length: int | None = None
        while True:
            header_line = await self._proc.stdout.readline()
            if not header_line:
                raise MCPTransportError("STDIO server closed stdout")

            line = header_line.decode("utf-8", errors="replace")
            stripped = line.strip("\r\n")

            if content_length is None:
                if not stripped:
                    continue
                if stripped.lower().startswith("content-length:"):
                    try:
                        content_length = int(stripped.split(":", 1)[1].strip())
                    except Exception as exc:
                        raise MCPProtocolError(f"Invalid Content-Length header: {stripped}") from exc
                else:
                    continue
            else:
                if stripped == "":
                    break

        body = await self._read_exactly(content_length)
        try:
            message = json.loads(body.decode("utf-8", errors="replace"))
        except Exception as exc:
            raise MCPProtocolError("Failed to parse STDIO JSON message") from exc

        if not isinstance(message, dict):
            raise MCPProtocolError("STDIO message must be a JSON object")
        return message

    async def _read_loop(self) -> None:
        """Dispatch subprocess responses to waiting futures."""
        try:
            while True:
                message = await self._read_message()

                if "id" in message and message.get("id") is not None:
                    raw_id = message.get("id")
                    key: str | None = None
                    if isinstance(raw_id, str):
                        key = raw_id
                    elif isinstance(raw_id, int):
                        key = str(raw_id)
                    elif isinstance(raw_id, float) and raw_id.is_integer():
                        key = str(int(raw_id))

                    if key is not None and key in self._pending:
                        future = self._pending.pop(key)
                        if message.get("error") is not None:
                            future.set_exception(MCPTransportError(f"MCP error: {message['error']}"))
                        else:
                            result = message.get("result")
                            if not isinstance(result, dict):
                                future.set_exception(MCPProtocolError("MCP result must be an object"))
                            else:
                                future.set_result(result)
        except Exception as exc:
            tail = self._stderr_tail()
            error: Exception
            if tail:
                error = MCPTransportError(f"STDIO read loop error: {exc}; stderr tail: {tail.strip()}")
            else:
                error = exc
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(error)
            self._pending.clear()
            raise

    async def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request over stdio and await the result."""
        if self._proc is None or self._proc.stdin is None:
            raise MCPTransportError("Transport not connected")

        self._id += 1
        req_id = self._id
        key = str(req_id)

        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params

        future = asyncio.get_running_loop().create_future()
        self._pending[key] = future

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        framing = str(self.cfg.framing).lower().strip()
        if framing in ("newline", "ndjson", "jsonl"):
            self._proc.stdin.write(body + b"\n")
        else:
            header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
            self._proc.stdin.write(header + body)
        await self._proc.stdin.drain()

        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError as exc:
            tail = self._stderr_tail()
            message = f"STDIO request timed out after 30.0s: method={method}"
            if tail:
                message = message + f"; stderr tail: {tail.strip()}"
            raise MCPTransportError(message) from exc
        finally:
            self._pending.pop(key, None)

    async def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification over stdio."""
        if self._proc is None or self._proc.stdin is None:
            raise MCPTransportError("Transport not connected")

        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        framing = str(self.cfg.framing).lower().strip()
        if framing in ("newline", "ndjson", "jsonl"):
            self._proc.stdin.write(body + b"\n")
        else:
            header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
            self._proc.stdin.write(header + body)
        await self._proc.stdin.drain()
