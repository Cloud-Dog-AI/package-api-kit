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

# cloud_dog_api_kit — Test flow templates
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Reusable test flow templates for auth, CRUD, jobs, and streaming.
# Related requirements: FR17.1
# Related architecture: SA1

"""Reusable flow templates for cloud_dog_api_kit testing."""

from __future__ import annotations

from cloud_dog_api_kit.testing.flows.auth_flow import AuthFlow
from cloud_dog_api_kit.testing.flows.crud_flow import CRUDFlow
from cloud_dog_api_kit.testing.flows.job_flow import JobFlow
from cloud_dog_api_kit.testing.flows.streaming_flow import StreamingFlow

__all__ = ["AuthFlow", "CRUDFlow", "JobFlow", "StreamingFlow"]
