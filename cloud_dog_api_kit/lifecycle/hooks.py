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

# cloud_dog_api_kit — Startup lifecycle hook definitions
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Deterministic startup/shutdown hook model for create_app()
#   lifecycle integration.
# Related requirements: FR18.2
# Related architecture: SA1

"""Lifecycle hook definitions for cloud_dog_api_kit."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable

from fastapi import FastAPI

LifecycleCallback = Callable[[FastAPI], Awaitable[None] | None]


async def _run_callback(phase: str, app: FastAPI, callback: LifecycleCallback | None) -> None:
    """Run a lifecycle callback if configured."""
    if callback is None:
        return
    result = callback(app)
    if inspect.isawaitable(result):
        await result
    if result is not None and not inspect.isawaitable(result):
        # Guard against accidental non-None return values in lifecycle callbacks.
        raise TypeError(f"Lifecycle callback for {phase} must return None or awaitable None")


@dataclass(slots=True)
class LifecycleHooks:
    """Startup/shutdown lifecycle hook collection.

    Phases:
    - `on_pre_db`: pre-database bootstrap phase.
    - `on_post_db`: post-database, pre-router phase.
    - `on_post_router`: post-router registration, pre-serving phase.
    - `on_shutdown`: graceful shutdown callback.

    Related tests: UT1.38_StartupLifecycleHooks, ST1.13_StartupLifecycleIntegration
    """

    on_pre_db: LifecycleCallback | None = None
    on_post_db: LifecycleCallback | None = None
    on_post_router: LifecycleCallback | None = None
    on_shutdown: LifecycleCallback | None = None

    async def run_startup(self, app: FastAPI) -> None:
        """Run startup phases in deterministic order."""
        await _run_callback("on_pre_db", app, self.on_pre_db)
        await _run_callback("on_post_db", app, self.on_post_db)
        await _run_callback("on_post_router", app, self.on_post_router)

    async def run_shutdown(self, app: FastAPI) -> None:
        """Run shutdown hook."""
        await _run_callback("on_shutdown", app, self.on_shutdown)
