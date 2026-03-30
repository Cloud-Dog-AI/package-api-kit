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

# cloud_dog_api_kit — Correlation ID context and middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Context-local correlation ID, app ID, and host ID management
#   with ASGI middleware for automatic extraction/propagation.
# Related requirements: FR5.1, FR3.2
# Related architecture: CC1.8

"""Correlation ID context and middleware for cloud_dog_api_kit."""

from cloud_dog_api_kit.correlation.context import (
    get_app_id,
    get_correlation_id,
    get_host_id,
    get_request_id,
    set_app_id,
    set_correlation_id,
    set_host_id,
    set_request_id,
    clear_context,
)
from cloud_dog_api_kit.correlation.middleware import CorrelationMiddleware

__all__ = [
    "get_app_id",
    "get_correlation_id",
    "get_host_id",
    "get_request_id",
    "set_app_id",
    "set_correlation_id",
    "set_host_id",
    "set_request_id",
    "clear_context",
    "CorrelationMiddleware",
]
