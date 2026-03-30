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

# cloud_dog_api_kit — Router helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Router factories (CRUD, health, jobs, version) for consistent
#   API structure.
# Related requirements: FR4.1, FR4.2, FR6.1, FR7.1
# Related architecture: SA1

"""Router helpers for cloud_dog_api_kit."""

from __future__ import annotations

from cloud_dog_api_kit.routers.crud import CRUDService, create_crud_router, create_versioned_router
from cloud_dog_api_kit.routers.health import HealthCheck, create_health_router
from cloud_dog_api_kit.routers.jobs import create_job_endpoint
from cloud_dog_api_kit.routers.version import create_version_router

__all__ = [
    "CRUDService",
    "create_crud_router",
    "create_versioned_router",
    "HealthCheck",
    "create_health_router",
    "create_job_endpoint",
    "create_version_router",
]
