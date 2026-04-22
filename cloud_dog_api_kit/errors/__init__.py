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

# cloud_dog_api_kit — Error taxonomy and exception hierarchy
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Typed exception classes mapping to the PS-20 error taxonomy.
# Related requirements: FR1.3, FR2.1, FR2.2
# Related architecture: CC1.3

"""Error taxonomy and exception hierarchy for cloud_dog_api_kit."""

from cloud_dog_api_kit.errors.exceptions import (
    APIError,
    ConflictError,
    InternalError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    UnauthenticatedError,
    UnauthorisedError,
    UpstreamError,
    ValidationError,
)
from cloud_dog_api_kit.errors.handler import register_error_handlers

__all__ = [
    "APIError",
    "ConflictError",
    "InternalError",
    "NotFoundError",
    "RateLimitError",
    "TimeoutError",
    "UnauthenticatedError",
    "UnauthorisedError",
    "UpstreamError",
    "ValidationError",
    "register_error_handlers",
]
