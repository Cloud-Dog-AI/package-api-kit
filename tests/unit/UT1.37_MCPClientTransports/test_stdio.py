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

"""UT1.37 stdio MCP transport coverage."""

from __future__ import annotations

import sys

import pytest

from cloud_dog_api_kit.mcp.client_transport import StdioConfig, StdioTransport


STDIO_SERVER = r"""
import json
import sys

framing = sys.argv[1]

def write_message(message):
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    if framing == "newline":
        sys.stdout.write(body.decode("utf-8") + "\n")
        sys.stdout.flush()
        return
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body)
    sys.stdout.buffer.flush()

def read_message():
    if framing == "newline":
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        return json.loads(line)
    length = None
    while True:
        header = sys.stdin.buffer.readline()
        if not header:
            raise EOFError
        text = header.decode("utf-8")
        stripped = text.strip("\r\n")
        if length is None:
            if not stripped:
                continue
            if stripped.lower().startswith("content-length:"):
                length = int(stripped.split(":", 1)[1].strip())
        else:
            if stripped == "":
                break
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))

while True:
    try:
        message = read_message()
    except EOFError:
        break
    if "id" not in message:
        continue
    write_message({"jsonrpc": "2.0", "id": message["id"], "result": {"echo": message["method"]}})
"""


@pytest.mark.asyncio
class TestStdioTransport:
    async def test_content_length_framing_round_trip(self) -> None:
        transport = StdioTransport(
            StdioConfig(
                command=sys.executable,
                args=["-c", STDIO_SERVER, "content_length"],
            )
        )

        await transport.connect()
        try:
            result = await transport.request("tools/list")
        finally:
            await transport.close()

        assert result == {"echo": "tools/list"}

    async def test_newline_framing_round_trip(self) -> None:
        transport = StdioTransport(
            StdioConfig(
                command=sys.executable,
                args=["-c", STDIO_SERVER, "newline"],
                framing="newline",
            )
        )

        await transport.connect()
        try:
            result = await transport.request("resources/list")
        finally:
            await transport.close()

        assert result == {"echo": "resources/list"}
