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

# cloud_dog_api_kit — CORS configuration helper
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: CORS middleware configuration with production-safe defaults.
#   Does not use wildcard origins unless explicitly configured.
# Related requirements: FR11.1, CS1.4
# Related architecture: CC1.12

"""CORS configuration helper for cloud_dog_api_kit."""

from __future__ import annotations


from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware


def configure_cors(
    app: FastAPI,
    allowed_origins: list[str] | None = None,
    allow_credentials: bool = True,
    allow_methods: list[str] | None = None,
    allow_headers: list[str] | None = None,
) -> None:
    """Configure CORS middleware on a FastAPI application.

    Production-safe defaults: explicit origins only, not wildcard ``*``
    unless explicitly provided.

    Args:
        app: The FastAPI application.
        allowed_origins: List of allowed origins. Defaults to empty (no CORS).
        allow_credentials: Whether to allow credentials. Defaults to True.
        allow_methods: Allowed HTTP methods. Defaults to standard set.
        allow_headers: Allowed headers. Defaults to standard set.

    Related tests: UT1.25_CORSHelper
    """
    origins = allowed_origins or []
    methods = allow_methods or ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    headers = allow_headers or [
        "Authorization",
        "X-API-Key",
        "X-Request-Id",
        "X-Correlation-Id",
        "X-App-Id",
        "X-Host-Id",
        "Content-Type",
        "Accept",
        "Idempotency-Key",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=methods,
        allow_headers=headers,
    )
