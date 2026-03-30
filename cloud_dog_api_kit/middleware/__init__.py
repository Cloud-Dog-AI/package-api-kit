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

# cloud_dog_api_kit — Middleware components
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Standard middleware components (logging, CORS, timing, timeout).
# Related requirements: FR11.1, FR12.1, FR13.1
# Related architecture: SA1

"""Middleware components for cloud_dog_api_kit."""

from __future__ import annotations

from cloud_dog_api_kit.middleware.cors import configure_cors
from cloud_dog_api_kit.middleware.logging import RequestLoggingMiddleware
from cloud_dog_api_kit.middleware.request_size_limit import RequestSizeLimitMiddleware
from cloud_dog_api_kit.middleware.timing import TimingMiddleware
from cloud_dog_api_kit.middleware.timeout import TimeoutMiddleware

__all__ = [
    "RequestLoggingMiddleware",
    "RequestSizeLimitMiddleware",
    "TimingMiddleware",
    "TimeoutMiddleware",
    "configure_cors",
]
