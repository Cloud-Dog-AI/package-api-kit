# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""A2A agent card and task submission router.

Provides ``create_a2a_card_router`` which adds:
- ``GET /.well-known/agent.json`` — agent card per A2A protocol spec
- ``POST /a2a/tasks`` — task submission that routes to skill handlers

Usage in any service's A2A server::

    from cloud_dog_api_kit.a2a.card import create_a2a_card_router, A2ASkill

    skills = [
        A2ASkill(id="search", name="Search", description="Semantic search",
                 handler=lambda text: service.search(query=text)),
    ]
    router = create_a2a_card_router(
        name="index-retriever",
        description="Vector database search and document ingestion",
        url="https://example.invalid/a2a",
        skills=skills,
    )
    app.include_router(router)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


@dataclass
class A2ASkill:
    """A skill exposed via the A2A agent card."""

    id: str
    name: str
    description: str
    handler: Callable[[str], Any] | None = None


def create_a2a_card_router(
    *,
    name: str,
    description: str,
    url: str = "",
    version: str = "1.0.0",
    skills: list[A2ASkill] | None = None,
) -> APIRouter:
    """Create a FastAPI router with A2A agent card and task submission.

    Args:
        name: Service name for the agent card.
        description: Human-readable service description.
        url: Base URL for the A2A endpoint.
        version: Service version string.
        skills: List of skills to expose. Each skill can have a handler
            function that accepts a text input and returns a result.

    Returns:
        A FastAPI APIRouter with agent card and task routes.
    """
    _skills = skills or []
    _skill_map: dict[str, A2ASkill] = {s.id: s for s in _skills}

    card = {
        "name": name,
        "description": description,
        "url": url,
        "version": version,
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": [
            {"id": s.id, "name": s.name, "description": s.description}
            for s in _skills
        ],
    }

    router = APIRouter()

    @router.get("/.well-known/agent.json")
    async def agent_card() -> JSONResponse:
        """Return the A2A agent card as JSON."""
        return JSONResponse(card)

    @router.post("/a2a/tasks")
    @router.post("/tasks")
    async def submit_task(request: Request) -> JSONResponse:
        """Accept an A2A task submission and dispatch to the matching skill."""
        body = await request.json()
        task_id = body.get("id", str(uuid4()))
        skill_id = body.get("skill_id", "")
        input_data = body.get("input", {})
        input_text = input_data.get("text", "") if isinstance(input_data, dict) else str(input_data)

        skill = _skill_map.get(skill_id)
        if skill is None:
            # If no specific skill, try a generic "health" skill
            if skill_id == "health":
                return JSONResponse({
                    "id": task_id,
                    "status": "completed",
                    "output": {"type": "text", "text": f"{name} is healthy"},
                })
            return JSONResponse(
                {"id": task_id, "status": "failed",
                 "error": f"Unknown skill: {skill_id}. Available: {list(_skill_map.keys())}"},
                status_code=404,
            )

        try:
            if skill.handler is not None:
                result = skill.handler(input_text)
                # Handle async handlers
                import asyncio
                if asyncio.iscoroutine(result):
                    result = await result
                result_text = str(result)
            else:
                result_text = f"Skill '{skill_id}' acknowledged (no handler configured)"
        except Exception as exc:
            return JSONResponse({
                "id": task_id,
                "status": "failed",
                "error": str(exc),
            })

        return JSONResponse({
            "id": task_id,
            "status": "completed",
            "output": {"type": "text", "text": result_text},
        })

    return router
