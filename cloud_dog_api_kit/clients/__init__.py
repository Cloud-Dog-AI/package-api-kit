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

# cloud_dog_api_kit — HTTP client helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Service-to-service HTTP client creation and retry utilities.
# Related requirements: FR9.1, FR9.2
# Related architecture: SA1

"""HTTP client helpers for cloud_dog_api_kit."""

from __future__ import annotations

from cloud_dog_api_kit.clients.http_client import ClientTimeout, RetryPolicy, create_http_client

__all__ = ["ClientTimeout", "RetryPolicy", "create_http_client"]
