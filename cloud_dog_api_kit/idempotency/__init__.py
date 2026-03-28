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

# cloud_dog_api_kit — Idempotency middleware and store
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Idempotency-Key header support with pluggable storage backend.
# Related requirements: FR4.4
# Related architecture: CC1.16

"""Idempotency middleware and store for cloud_dog_api_kit."""

from cloud_dog_api_kit.idempotency.middleware import IdempotencyMiddleware
from cloud_dog_api_kit.idempotency.store import IdempotencyStore, InMemoryIdempotencyStore

__all__ = ["IdempotencyMiddleware", "IdempotencyStore", "InMemoryIdempotencyStore"]
