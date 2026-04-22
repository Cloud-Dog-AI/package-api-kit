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

# cloud_dog_api_kit — Configuration model
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Settings model for wiring cloud_dog_api_kit in a service. This
#   module intentionally keeps configuration minimal and provider-agnostic.
# Related requirements: FR10.3, FR11.1, FR13.1
# Related architecture: SA1

"""Configuration model for cloud_dog_api_kit."""

from __future__ import annotations

from pydantic import BaseModel, Field


class APIKitSettings(BaseModel):
    """Settings for cloud_dog_api_kit.

    These settings can be sourced from `cloud_dog_config` when available, but
    are also usable standalone (e.g. local tests).
    """

    api_prefix: str = Field(default="/api/v1", description="API prefix for versioned routes")
    api_version: str = Field(default="v1", description="API version string for headers and metadata")
    enable_docs: bool = Field(default=True, description="Whether to enable /docs and /redoc")
    enable_request_logging: bool = Field(default=True, description="Whether to enable request logging middleware")
    enable_cors: bool = Field(default=True, description="Whether to enable CORS middleware")
    cors_origins: list[str] = Field(default_factory=list, description="Allowed CORS origins")
    timeout_seconds: float = Field(default=30.0, ge=0.1, description="Request timeout in seconds")
    max_request_body_bytes: int | None = Field(
        default=None,
        ge=1,
        description="Maximum request body size in bytes; None disables size checks",
    )
    shutdown_drain_timeout_seconds: float = Field(
        default=5.0,
        ge=0.0,
        description="Graceful shutdown request-drain timeout in seconds",
    )
