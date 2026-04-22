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

# cloud_dog_api_kit — Compatibility and migration exports
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Migration compatibility middleware exports.
# Related requirements: FR18.3, FR18.4, FR18.6
# Related architecture: SA1

"""Compatibility middleware exports."""

from __future__ import annotations

from cloud_dog_api_kit.compat.envelope import LegacyEnvelopeMiddleware, legacy_envelope_route
from cloud_dog_api_kit.compat.profile import ProfileContextMiddleware
from cloud_dog_api_kit.compat.routes import LegacyRouteAdapter, LegacyRouteAdapterMiddleware

__all__ = [
    "LegacyEnvelopeMiddleware",
    "LegacyRouteAdapter",
    "LegacyRouteAdapterMiddleware",
    "ProfileContextMiddleware",
    "legacy_envelope_route",
]
