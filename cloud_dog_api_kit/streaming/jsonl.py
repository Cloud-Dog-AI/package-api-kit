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

# cloud_dog_api_kit — JSONL streaming helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Line-delimited JSON streaming endpoint helpers.
# Related requirements: FR8.1, FR8.3
# Related architecture: CC1.14

"""JSONL streaming helpers for cloud_dog_api_kit."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from starlette.responses import StreamingResponse

from cloud_dog_api_kit.correlation.context import get_request_id


async def _jsonl_generator(data_generator: AsyncGenerator) -> AsyncGenerator[str, None]:
    """Wrap an async generator to produce JSONL output.

    Args:
        data_generator: Async generator yielding dicts or serialisable objects.

    Yields:
        JSON Lines strings (one JSON object per line).
    """
    request_id = get_request_id()
    async for item in data_generator:
        if isinstance(item, dict):
            item["request_id"] = request_id
            yield json.dumps(item, default=str) + "\n"
        else:
            yield json.dumps({"data": item, "request_id": request_id}, default=str) + "\n"


def create_jsonl_endpoint(data_generator: AsyncGenerator) -> StreamingResponse:
    """Create a StreamingResponse for JSONL output.

    Args:
        data_generator: Async generator yielding data items.

    Returns:
        A StreamingResponse with ``application/x-ndjson`` content type.

    Related tests: UT1.21_JSONLStreaming
    """
    return StreamingResponse(
        content=_jsonl_generator(data_generator),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )
