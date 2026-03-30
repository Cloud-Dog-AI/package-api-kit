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

# cloud_dog_api_kit — Service-to-service authentication
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Service-to-service auth using X-App-Id + service key.
# Related requirements: FR3.5
# Related architecture: SA1

"""Service-to-service authentication helpers."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Header

from cloud_dog_api_kit.errors.exceptions import UnauthenticatedError


def create_service_auth_dependency(
    service_key_verify_fn: Callable[[str, str], dict[str, Any] | None],
    app_id_header: str = "X-App-Id",
    key_header: str = "X-Service-Key",
) -> Callable:
    """Create a dependency enforcing service-to-service authentication."""

    async def _dep(
        app_id: str | None = Header(default=None, alias=app_id_header),
        service_key: str | None = Header(default=None, alias=key_header),
    ) -> dict[str, Any]:
        if not app_id or not service_key:
            raise UnauthenticatedError(message="Missing service credentials")

        result = service_key_verify_fn(app_id, service_key)
        if result is None:
            raise UnauthenticatedError(message="Invalid service credentials")

        return result

    return _dep
