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

# cloud_dog_api_kit — Correlation context using contextvars
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Context-local storage for request ID, correlation ID, app ID,
#   and host ID. Uses contextvars for async-safe propagation.
# Related requirements: FR5.1, FR3.2, NF1.3
# Related architecture: CC1.8

"""Correlation context management using contextvars."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_app_id_var: ContextVar[str | None] = ContextVar("app_id", default=None)
_host_id_var: ContextVar[str | None] = ContextVar("host_id", default=None)


def get_request_id() -> str:
    """Get the current request ID, generating one if not set.

    Returns:
        The request ID string.
    """
    rid = _request_id_var.get()
    if rid is None:
        rid = uuid.uuid4().hex
        _request_id_var.set(rid)
    return rid


def set_request_id(rid: str) -> None:
    """Set the request ID for the current context.

    Args:
        rid: The request ID to set.
    """
    _request_id_var.set(rid)


def get_correlation_id() -> str | None:
    """Get the cross-service correlation ID, if set.

    Returns:
        The correlation ID string or None.
    """
    return _correlation_id_var.get()


def set_correlation_id(cid: str) -> None:
    """Set the cross-service correlation ID.

    Args:
        cid: The correlation ID to set.
    """
    _correlation_id_var.set(cid)


def get_app_id() -> str | None:
    """Get the calling application ID, if set.

    Returns:
        The app ID string or None.
    """
    return _app_id_var.get()


def set_app_id(app_id: str) -> None:
    """Set the calling application ID.

    Args:
        app_id: The app ID to set.
    """
    _app_id_var.set(app_id)


def get_host_id() -> str | None:
    """Get the host ID, if set.

    Returns:
        The host ID string or None.
    """
    return _host_id_var.get()


def set_host_id(host_id: str) -> None:
    """Set the host ID.

    Args:
        host_id: The host ID to set.
    """
    _host_id_var.set(host_id)


def clear_context() -> None:
    """Clear all correlation context variables."""
    _request_id_var.set(None)
    _correlation_id_var.set(None)
    _app_id_var.set(None)
    _host_id_var.set(None)
