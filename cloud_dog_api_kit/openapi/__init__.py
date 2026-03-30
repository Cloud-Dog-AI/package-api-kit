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

# cloud_dog_api_kit — OpenAPI customisation helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Helpers for OpenAPI schema customisation and versioning.
# Related requirements: FR10.1, FR10.2, FR10.4
# Related architecture: CC1.17

"""OpenAPI customisation helpers for cloud_dog_api_kit."""

from __future__ import annotations

from cloud_dog_api_kit.openapi.customise import configure_openapi
from cloud_dog_api_kit.openapi.route import create_openapi_router

__all__ = ["configure_openapi", "create_openapi_router"]
