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

"""UT1.38: Deterministic startup lifecycle hook ordering."""

from __future__ import annotations

import pytest

from cloud_dog_api_kit.factory import create_app
from cloud_dog_api_kit.lifecycle import LifecycleHooks


@pytest.mark.asyncio
class TestStartupLifecycleHooks:
    async def test_startup_hooks_execute_in_order(self) -> None:
        events: list[str] = []

        async def on_pre_db(_app) -> None:
            events.append("pre_db")

        async def on_post_db(_app) -> None:
            events.append("post_db")

        async def on_post_router(_app) -> None:
            events.append("post_router")

        app = create_app(
            title="Lifecycle Test",
            lifecycle_hooks=LifecycleHooks(
                on_pre_db=on_pre_db,
                on_post_db=on_post_db,
                on_post_router=on_post_router,
            ),
            register_signal_handlers_on_startup=False,
        )

        async with app.router.lifespan_context(app):
            pass

        assert events == ["pre_db", "post_db", "post_router"]

    async def test_hook_failure_prevents_startup(self) -> None:
        async def on_pre_db(_app) -> None:
            raise RuntimeError("bootstrap failed")

        app = create_app(
            title="Lifecycle Failure",
            lifecycle_hooks=LifecycleHooks(on_pre_db=on_pre_db),
            register_signal_handlers_on_startup=False,
        )

        with pytest.raises(RuntimeError, match="bootstrap failed"):
            async with app.router.lifespan_context(app):
                pass
