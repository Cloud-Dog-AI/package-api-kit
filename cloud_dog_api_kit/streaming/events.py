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

# cloud_dog_api_kit — Streaming event models
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Standard SSE event model and serialisation.
# Related requirements: FR8.2
# Related architecture: SA1

"""Streaming event models for cloud_dog_api_kit."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class SSEEvent:
    """Standard server-sent event payload.

    Related tests: UT1.22_SSEEventModel
    """

    type: str
    data: Any = None
    request_id: str = ""
    job_id: str | None = None

    def to_sse(self) -> str:
        """Serialise to SSE wire format."""
        payload = {"type": self.type, "data": self.data, "request_id": self.request_id, "job_id": self.job_id}
        return f"event: {self.type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
