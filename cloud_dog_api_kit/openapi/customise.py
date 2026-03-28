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

# cloud_dog_api_kit — OpenAPI customisation
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Helpers for OpenAPI schema customisation, security schemes,
#   and documentation behaviours.
# Related requirements: FR10.1, FR10.2
# Related architecture: SA1, CC1.17

"""OpenAPI customisation helpers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


def configure_openapi(
    app: FastAPI,
    tags: list[dict] | None = None,
    security_schemes: dict | None = None,
) -> None:
    """Configure OpenAPI schema customisation on a FastAPI application.

    Args:
        app: The FastAPI application.
        tags: OpenAPI tag metadata for endpoint grouping.
        security_schemes: Security scheme definitions.

    Related tests: UT1.31_OpenAPICustomise
    """
    if tags:
        app.openapi_tags = tags

    if security_schemes:

        def _custom_openapi() -> dict[str, Any]:
            if app.openapi_schema:
                return app.openapi_schema
            from fastapi.openapi.utils import get_openapi

            schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
                tags=app.openapi_tags,
            )
            schema.setdefault("components", {})
            schema["components"]["securitySchemes"] = security_schemes
            app.openapi_schema = schema
            return schema

        app.openapi = _custom_openapi  # type: ignore[method-assign]
