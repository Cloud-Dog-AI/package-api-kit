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

# cloud_dog_api_kit — Response envelopes
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Standard success and error response envelopes per PS-20.
# Related requirements: FR1.1, FR1.2
# Related architecture: CC1.1

"""Standard response envelopes for cloud_dog_api_kit."""

from __future__ import annotations

from cloud_dog_api_kit.envelopes.error import ErrorDetail, ErrorResponse, error_envelope
from cloud_dog_api_kit.envelopes.success import Meta, SuccessResponse, success_envelope

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "Meta",
    "SuccessResponse",
    "success_envelope",
    "error_envelope",
]
