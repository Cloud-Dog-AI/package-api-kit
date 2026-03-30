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

"""UT1.22: SSE Event Model — event serialisation tests."""

from __future__ import annotations
import json
from cloud_dog_api_kit.streaming.sse import SSEEvent


class TestSSEEventModel:
    def test_to_sse_contains_event_line(self) -> None:
        e = SSEEvent(type="started", data={"msg": "begin"}, request_id="r-1")
        output = e.to_sse()
        assert output.startswith("event: started\n")

    def test_to_sse_data_is_json(self) -> None:
        e = SSEEvent(type="delta", data={"text": "hi"}, request_id="r-1")
        output = e.to_sse()
        data_line = [line for line in output.split("\n") if line.startswith("data:")][0]
        payload = json.loads(data_line[5:].strip())
        assert payload["type"] == "delta"
        assert payload["data"]["text"] == "hi"

    def test_to_sse_includes_request_id(self) -> None:
        e = SSEEvent(type="completed", request_id="r-99")
        output = e.to_sse()
        assert "r-99" in output

    def test_to_sse_includes_job_id_when_set(self) -> None:
        e = SSEEvent(type="progress", data={}, request_id="r-1", job_id="j-5")
        output = e.to_sse()
        assert "j-5" in output

    def test_to_sse_ends_with_double_newline(self) -> None:
        e = SSEEvent(type="error", data={"message": "fail"}, request_id="r-1")
        assert e.to_sse().endswith("\n\n")
