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

# cloud_dog_api_kit — Streaming flow template
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Reusable streaming flow checks for SSE/JSONL endpoints.
# Related requirements: FR8.1
# Related architecture: SA1

"""Streaming flow template for tests."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class StreamingFlow:
    """Reusable streaming flow assertions."""

    path: str

    async def fetch_stream(self, client: httpx.AsyncClient) -> str:
        """Handle fetch stream."""
        r = await client.get(self.path)
        r.raise_for_status()
        return r.text
