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

# cloud_dog_api_kit — Streaming helpers (SSE, JSONL)
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Helpers for creating SSE and JSONL streaming endpoints.
# Related requirements: FR8.1, FR8.2, FR8.3
# Related architecture: CC1.14

"""Streaming helpers for cloud_dog_api_kit."""

from cloud_dog_api_kit.streaming.sse import create_sse_endpoint, SSEEvent
from cloud_dog_api_kit.streaming.jsonl import create_jsonl_endpoint

__all__ = ["create_sse_endpoint", "create_jsonl_endpoint", "SSEEvent"]
