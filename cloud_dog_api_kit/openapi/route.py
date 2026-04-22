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

# cloud_dog_api_kit — OpenAPI spec route helper
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Provides a helper for serving an OpenAPI schema via a stable
#   endpoint.
# Related requirements: FR10.1
# Related architecture: SA1

"""OpenAPI spec route helper for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI


def create_openapi_router(
    app: FastAPI,
    path: str = "/openapi.json",
    tags: list[str] | None = None,
) -> APIRouter:
    """Create a router that serves the OpenAPI schema for the given app."""
    router = APIRouter(tags=tags or ["openapi"])

    @router.get(path)
    async def openapi_schema() -> dict[str, Any]:
        """Return the OpenAPI schema."""
        return app.openapi()

    return router
