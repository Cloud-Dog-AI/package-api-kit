# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0
"""A2A skill audit middleware tests. Requirements: PS-50.AUD2. Tasks: W28A-737."""

import logging

from cloud_dog_api_kit.a2a.skill_audit import a2a_skill_audit_middleware


def _make_handler():
    def handler(text, **kwargs):
        return f"processed: {text}"
    return handler


def _make_error_handler():
    def handler(text, **kwargs):
        raise RuntimeError("skill failed")
    return handler


def test_skill_audit_emits_on_success(caplog):
    """Successful skill invocation produces audit log."""
    handler = _make_handler()
    wrapped = a2a_skill_audit_middleware("read_file", handler, service="test-svc")
    with caplog.at_level(logging.INFO):
        result = wrapped("hello", task_id="task-123")
    assert result == "processed: hello"
    record = [r for r in caplog.records if "a2a_skill_invocation" in r.message][0]
    assert record.__dict__["outcome"] == "success"
    assert record.__dict__["skill_name"] == "read_file"


def test_skill_audit_emits_on_error(caplog):
    """Failed skill invocation produces audit log with error_detail."""
    handler = _make_error_handler()
    wrapped = a2a_skill_audit_middleware("fail_skill", handler, service="test-svc")
    try:
        with caplog.at_level(logging.WARNING):
            wrapped("test", task_id="task-456")
    except RuntimeError:
        pass
    record = [r for r in caplog.records if "a2a_skill_invocation" in r.message][0]
    assert record.__dict__["outcome"] == "error"
    assert "skill failed" in record.__dict__["error_detail"]


def test_skill_audit_includes_task_id(caplog):
    """A2A task ID is included in audit record."""
    handler = _make_handler()
    wrapped = a2a_skill_audit_middleware("test_skill", handler, service="test-svc")
    with caplog.at_level(logging.INFO):
        wrapped("data", task_id="my-task-789")
    record = [r for r in caplog.records if "a2a_skill_invocation" in r.message][0]
    assert record.__dict__["task_id"] == "my-task-789"


def test_skill_audit_includes_correlation_id(caplog):
    """Correlation ID is included (defaults to task_id)."""
    handler = _make_handler()
    wrapped = a2a_skill_audit_middleware("corr_skill", handler, service="test-svc")
    with caplog.at_level(logging.INFO):
        wrapped("data", task_id="corr-001")
    record = [r for r in caplog.records if "a2a_skill_invocation" in r.message][0]
    assert record.__dict__["correlation_id"] == "corr-001"
