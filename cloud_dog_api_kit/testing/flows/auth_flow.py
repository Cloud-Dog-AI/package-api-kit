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

# cloud_dog_api_kit — Auth flow template
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Reusable auth flow checks for services using cloud_dog_api_kit.
# Related requirements: FR3.1, FR3.4
# Related architecture: SA1

"""Auth flow template for tests."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class AuthFlow:
    """Reusable auth flow assertions."""

    protected_path: str

    async def assert_unauthenticated(self, client: httpx.AsyncClient) -> None:
        """Handle assert unauthenticated."""
        r = await client.get(self.protected_path)
        assert r.status_code == 401
