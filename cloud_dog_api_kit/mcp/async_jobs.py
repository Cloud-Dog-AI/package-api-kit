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

# cloud_dog_api_kit — MCP async job helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Shared async job-store protocol and in-memory reference
#   implementation for wait=false MCP tool calls.
# Related requirements: FR18.1
# Related architecture: SA1

"""Async MCP tool-call job helpers."""

from __future__ import annotations

import asyncio
import inspect
import threading
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

AsyncJobContext = dict[str, Any]
AsyncJobStatus = dict[str, Any]


class AsyncJobStore(Protocol):
    """Protocol for async MCP tool-call job stores."""

    def submit(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: AsyncJobContext,
    ) -> str | Awaitable[str]:
        """Submit a tool call for async execution and return a job id."""

    def get_status(self, job_id: str) -> AsyncJobStatus | Awaitable[AsyncJobStatus]:
        """Return the current status payload for a submitted job."""


class InMemoryAsyncJobStore:
    """In-memory async job store for local tests and simple service deployments."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, AsyncJobStatus] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def submit(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: AsyncJobContext,
    ) -> str:
        """Submit a tool call for background execution."""
        runner = context.get("runner")
        if not callable(runner):
            raise TypeError("async job context requires a callable 'runner'")

        result_formatter = context.get("result_formatter")
        if result_formatter is not None and not callable(result_formatter):
            raise TypeError("async job context 'result_formatter' must be callable when provided")

        job_id = f"job-{uuid.uuid4().hex}"
        with self._lock:
            self._jobs[job_id] = {"status": "pending", "tool_name": tool_name, "arguments": dict(arguments)}

        task = asyncio.create_task(self._run_job(job_id, runner, result_formatter))
        with self._lock:
            self._tasks[job_id] = task
        return job_id

    async def _run_job(
        self,
        job_id: str,
        runner: Callable[[], Any],
        result_formatter: Callable[[Any], Any] | None,
    ) -> None:
        """Execute a submitted async job and persist its lifecycle state."""
        with self._lock:
            job = dict(self._jobs.get(job_id) or {})
            job["status"] = "running"
            self._jobs[job_id] = job

        try:
            result = runner()
            if inspect.isawaitable(result):
                result = await result
            if result_formatter is not None:
                result = result_formatter(result)
            with self._lock:
                job = dict(self._jobs.get(job_id) or {})
                job["status"] = "completed"
                job["result"] = result
                job.pop("error", None)
                self._jobs[job_id] = job
        except Exception as exc:
            with self._lock:
                job = dict(self._jobs.get(job_id) or {})
                job["status"] = "failed"
                job["error"] = str(exc)
                self._jobs[job_id] = job
        finally:
            with self._lock:
                self._tasks.pop(job_id, None)

    def get_status(self, job_id: str) -> AsyncJobStatus:
        """Return the current status payload for a job id."""
        with self._lock:
            status = self._jobs.get(job_id)
            if status is None:
                return {"status": "not_found", "error": "Job not found"}
            return dict(status)
