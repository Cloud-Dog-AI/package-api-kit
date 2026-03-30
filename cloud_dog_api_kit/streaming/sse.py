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

# cloud_dog_api_kit — SSE streaming helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Server-Sent Events (SSE) streaming endpoint helpers with
#   standard event types per PS-20.
# Related requirements: FR8.1, FR8.2, FR8.3
# Related architecture: CC1.14

"""SSE streaming helpers for cloud_dog_api_kit."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from starlette.responses import StreamingResponse

from cloud_dog_api_kit.correlation.context import get_request_id
from cloud_dog_api_kit.streaming.events import SSEEvent

STANDARD_EVENT_TYPES = frozenset({"started", "delta", "progress", "tool_call", "completed", "error"})


async def _sse_generator(
    event_generator: AsyncGenerator,
    event_type_field: str = "type",
) -> AsyncGenerator[str, None]:
    """Wrap an async generator to produce SSE-formatted output.

    Args:
        event_generator: Async generator yielding event dicts or SSEEvent objects.
        event_type_field: The key in event dicts that specifies the event type.

    Yields:
        SSE-formatted strings.
    """
    request_id = get_request_id()
    try:
        async for event in event_generator:
            if isinstance(event, SSEEvent):
                if not event.request_id:
                    event.request_id = request_id
                yield event.to_sse()
            elif isinstance(event, dict):
                sse_event = SSEEvent(
                    type=event.get(event_type_field, "delta"),
                    data=event.get("data", event),
                    request_id=request_id,
                    job_id=event.get("job_id"),
                )
                yield sse_event.to_sse()
            else:
                yield f"event: delta\ndata: {json.dumps({'data': str(event), 'request_id': request_id})}\n\n"

        # Send completion event
        completion = SSEEvent(type="completed", request_id=request_id)
        yield completion.to_sse()

    except Exception as exc:
        error_event = SSEEvent(
            type="error",
            data={"message": str(exc)},
            request_id=request_id,
        )
        yield error_event.to_sse()


def create_sse_endpoint(
    event_generator: AsyncGenerator,
    event_type_field: str = "type",
) -> StreamingResponse:
    """Create a StreamingResponse for SSE output.

    Args:
        event_generator: Async generator yielding events.
        event_type_field: The key in event dicts for event type.

    Returns:
        A StreamingResponse with ``text/event-stream`` content type.

    Related tests: UT1.20_SSEStreaming, ST1.9_StreamingEndToEnd
    """
    return StreamingResponse(
        content=_sse_generator(event_generator, event_type_field),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
