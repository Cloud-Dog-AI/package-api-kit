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

# cloud_dog_api_kit — Lifecycle integration exports
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Public lifecycle and graceful shutdown exports.
# Related requirements: FR18.2, FR18.9
# Related architecture: SA1

"""Lifecycle exports for cloud_dog_api_kit."""

from __future__ import annotations

from cloud_dog_api_kit.lifecycle.hooks import LifecycleHooks
from cloud_dog_api_kit.lifecycle.shutdown import (
    GracefulShutdownManager,
    ShutdownDrainMiddleware,
    install_shutdown_signal_handlers,
)

__all__ = [
    "GracefulShutdownManager",
    "LifecycleHooks",
    "ShutdownDrainMiddleware",
    "install_shutdown_signal_handlers",
]
