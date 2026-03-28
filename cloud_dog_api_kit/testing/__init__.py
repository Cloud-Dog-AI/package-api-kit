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

# cloud_dog_api_kit — Test scaffolding (fixtures, conformance, flow templates)
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Reusable test fixtures, conformance validators, and baseline
#   flow templates for verifying API compliance.
# Related requirements: FR16.1, FR16.2, FR16.3
# Related architecture: CC1.19

"""Test scaffolding for cloud_dog_api_kit."""

from cloud_dog_api_kit.testing.fixtures import create_test_client, create_auth_headers
from cloud_dog_api_kit.testing.conformance import (
    validate_error_envelope,
    validate_success_envelope,
    validate_pagination_response,
    validate_correlation_id,
)
from cloud_dog_api_kit.testing.flows import AuthFlow, CRUDFlow, JobFlow, StreamingFlow

__all__ = [
    "create_test_client",
    "create_auth_headers",
    "validate_error_envelope",
    "validate_success_envelope",
    "validate_pagination_response",
    "validate_correlation_id",
    "AuthFlow",
    "CRUDFlow",
    "JobFlow",
    "StreamingFlow",
]
