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

"""UT1.21: JSONL Streaming — line-delimited JSON streaming tests."""

from __future__ import annotations
import pytest
from cloud_dog_api_kit.streaming.jsonl import create_jsonl_endpoint
from cloud_dog_api_kit.correlation.context import set_request_id


class TestJSONLStreaming:
    @pytest.mark.asyncio
    async def test_creates_ndjson_response(self) -> None:
        set_request_id("jsonl-test")

        async def gen():
            yield {"event": "row", "data": {"id": 1}}

        response = create_jsonl_endpoint(gen())
        assert response.media_type == "application/x-ndjson"
