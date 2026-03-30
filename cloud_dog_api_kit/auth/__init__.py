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

# cloud_dog_api_kit — Authentication and authorisation
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Auth dependency, RBAC helpers, and tenant isolation.
# Related requirements: FR3.1, FR3.2, FR3.3, FR3.4, FR3.5
# Related architecture: CC1.5, CC1.6

"""Authentication and authorisation for cloud_dog_api_kit."""

from cloud_dog_api_kit.auth.dependency import create_auth_dependency
from cloud_dog_api_kit.auth.rbac import require_admin, require_permission, require_tenant
from cloud_dog_api_kit.auth.service_auth import create_service_auth_dependency

__all__ = [
    "create_auth_dependency",
    "create_service_auth_dependency",
    "require_admin",
    "require_permission",
    "require_tenant",
]
