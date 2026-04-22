# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0
"""MCP tool audit middleware tests. Requirements: PS-50.AUD1. Tasks: W28A-737."""

import logging

from cloud_dog_api_kit.mcp.tool_audit import mcp_tool_audit_middleware


def _make_handler(result="ok"):
    def handler(**kwargs):
        return {"result": result, **kwargs}
    return handler


def _make_error_handler():
    def handler(**kwargs):
        raise RuntimeError("tool failed")
    return handler


def test_audit_emits_on_success(caplog):
    """Successful tool call produces audit log with outcome=success."""
    handler = _make_handler()
    wrapped = mcp_tool_audit_middleware("test_tool", handler, service="test-svc")
    with caplog.at_level(logging.INFO):
        result = wrapped(path="/tmp/test")
    assert result["result"] == "ok"
    assert any("mcp_tool_call" in r.message and r.levelno == logging.INFO for r in caplog.records)
    record = [r for r in caplog.records if "mcp_tool_call" in r.message][0]
    assert record.__dict__["event_type"] == "mcp_tool_call"
    assert record.__dict__["outcome"] == "success"
    assert record.__dict__["tool_name"] == "test_tool"
    assert record.__dict__["service"] == "test-svc"


def test_audit_emits_on_error(caplog):
    """Failed tool call produces audit log with outcome=error."""
    handler = _make_error_handler()
    wrapped = mcp_tool_audit_middleware("fail_tool", handler, service="test-svc")
    try:
        with caplog.at_level(logging.WARNING):
            wrapped()
    except RuntimeError:
        pass
    record = [r for r in caplog.records if "mcp_tool_call" in r.message][0]
    assert record.__dict__["outcome"] == "error"
    assert "tool failed" in record.__dict__["error_detail"]


def test_audit_redacts_sensitive_params(caplog):
    """Parameters named password/secret/token are redacted."""
    handler = _make_handler()
    wrapped = mcp_tool_audit_middleware("secure_tool", handler, service="test-svc")
    with caplog.at_level(logging.INFO):
        wrapped(password="s3cret", token="tok123", path="/ok")
    record = [r for r in caplog.records if "mcp_tool_call" in r.message][0]
    params = record.__dict__["parameters"]
    assert params["password"] == "[REDACTED]"
    assert params["token"] == "[REDACTED]"
    assert params["path"] == "/ok"


def test_audit_includes_correlation_id(caplog):
    """Correlation ID is included in audit record."""
    handler = _make_handler()
    wrapped = mcp_tool_audit_middleware("corr_tool", handler, service="test-svc")
    with caplog.at_level(logging.INFO):
        wrapped()
    record = [r for r in caplog.records if "mcp_tool_call" in r.message][0]
    assert record.__dict__["correlation_id"]


def test_audit_measures_duration(caplog):
    """Duration_ms is a positive number."""
    handler = _make_handler()
    wrapped = mcp_tool_audit_middleware("dur_tool", handler, service="test-svc")
    with caplog.at_level(logging.INFO):
        wrapped()
    record = [r for r in caplog.records if "mcp_tool_call" in r.message][0]
    assert record.__dict__["duration_ms"] >= 0
