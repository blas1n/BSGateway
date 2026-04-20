"""Tests for worker.config — WorkerSettings."""

from __future__ import annotations

import socket

import pytest


def test_default_values() -> None:
    """WorkerSettings defaults are sensible."""
    from worker.config import WorkerSettings

    s = WorkerSettings(server_url="http://localhost:8000")
    assert s.server_url == "http://localhost:8000"
    assert s.worker_token == ""
    assert s.worker_name == socket.gethostname()
    assert s.poll_interval_seconds == 5
    assert s.max_parallel_tasks == 5
    assert s.skip_permissions is True


def test_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings load from BSGATEWAY_ prefixed env vars."""
    from worker.config import WorkerSettings

    monkeypatch.setenv("BSGATEWAY_SERVER_URL", "https://gw.example.com")
    monkeypatch.setenv("BSGATEWAY_WORKER_TOKEN", "tok-123")
    monkeypatch.setenv("BSGATEWAY_POLL_INTERVAL_SECONDS", "10")
    monkeypatch.setenv("BSGATEWAY_MAX_PARALLEL_TASKS", "3")
    monkeypatch.setenv("BSGATEWAY_SKIP_PERMISSIONS", "false")

    s = WorkerSettings()
    assert s.server_url == "https://gw.example.com"
    assert s.worker_token == "tok-123"
    assert s.poll_interval_seconds == 10
    assert s.max_parallel_tasks == 3
    assert s.skip_permissions is False
