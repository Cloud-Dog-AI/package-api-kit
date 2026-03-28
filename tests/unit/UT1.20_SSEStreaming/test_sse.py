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

"""UT1.20: SSE Streaming — Server-Sent Events streaming tests."""

from __future__ import annotations
import pytest
from cloud_dog_api_kit.streaming.sse import SSEEvent, create_sse_endpoint
from cloud_dog_api_kit.correlation.context import set_request_id


class TestSSEStreaming:
    def test_sse_event_to_sse_format(self) -> None:
        e = SSEEvent(type="delta", data={"text": "hello"}, request_id="r-1")
        output = e.to_sse()
        assert output.startswith("event: delta\n")
        assert "data:" in output
        assert "hello" in output
        assert output.endswith("\n\n")

    def test_sse_event_with_job_id(self) -> None:
        e = SSEEvent(type="started", data={}, request_id="r-1", job_id="j-1")
        output = e.to_sse()
        assert "j-1" in output

    def test_standard_event_types(self) -> None:
        from cloud_dog_api_kit.streaming.sse import STANDARD_EVENT_TYPES

        expected = {"started", "delta", "progress", "tool_call", "completed", "error"}
        assert STANDARD_EVENT_TYPES == expected

    @pytest.mark.asyncio
    async def test_create_sse_endpoint_returns_streaming_response(self) -> None:
        set_request_id("sse-test")

        async def gen():
            yield SSEEvent(type="delta", data={"text": "chunk"})

        response = create_sse_endpoint(gen())
        assert response.media_type == "text/event-stream"
