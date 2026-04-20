"""Tests for execute/tasks API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from bsgateway.api.app import create_app
from bsgateway.api.deps import get_auth_context
from bsgateway.streams import RedisStreamManager
from bsgateway.tests.conftest import make_gateway_auth_context, make_mock_pool

TENANT_ID = uuid4()
TASK_ID = uuid4()
WORKER_ID = uuid4()


@pytest.fixture
def mock_pool():
    pool, conn = make_mock_pool()
    return pool, conn


@pytest.fixture
def mock_stream_manager() -> AsyncMock:
    sm = AsyncMock(spec=RedisStreamManager)
    sm.publish.return_value = "msg-001"
    return sm


@pytest.fixture
def app(mock_pool, mock_stream_manager):
    pool, _conn = mock_pool
    app = create_app()
    app.state.db_pool = pool
    app.state.encryption_key = b"\x00" * 32
    app.state.redis = MagicMock()
    app.state.stream_manager = mock_stream_manager
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def tenant_ctx():
    return make_gateway_auth_context(tenant_id=TENANT_ID)


def _task_row(
    task_id=TASK_ID,
    tenant_id=TENANT_ID,
    status: str = "pending",
    worker_id=None,
    output: str | None = None,
) -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "id": task_id,
        "tenant_id": tenant_id,
        "executor_type": "claude_code",
        "prompt": "Write tests",
        "status": status,
        "worker_id": worker_id,
        "output": output,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }


class TestSubmitTask:
    def test_creates_task_and_dispatches(
        self, app, client: TestClient, tenant_ctx, mock_pool, mock_stream_manager
    ) -> None:
        _pool, conn = mock_pool
        # First fetchrow: create_task, second: find_available_worker
        conn.fetchrow.side_effect = [
            {"id": TASK_ID},
            {"id": WORKER_ID},
        ]
        conn.execute = AsyncMock()
        app.dependency_overrides[get_auth_context] = lambda: tenant_ctx

        resp = client.post(
            "/api/v1/execute",
            json={"executor_type": "claude_code", "prompt": "Write tests"},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["task_id"] == str(TASK_ID)
        assert body["status"] == "dispatched"
        mock_stream_manager.publish.assert_awaited_once()

    def test_no_worker_returns_pending(
        self, app, client: TestClient, tenant_ctx, mock_pool, mock_stream_manager
    ) -> None:
        _pool, conn = mock_pool
        conn.fetchrow.side_effect = [
            {"id": TASK_ID},
            None,  # no available worker
        ]
        app.dependency_overrides[get_auth_context] = lambda: tenant_ctx

        resp = client.post(
            "/api/v1/execute",
            json={"executor_type": "claude_code", "prompt": "hello"},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "pending"
        mock_stream_manager.publish.assert_not_awaited()


class TestGetTask:
    def test_returns_task(self, app, client: TestClient, tenant_ctx, mock_pool) -> None:
        _pool, conn = mock_pool
        conn.fetchrow.return_value = _task_row(status="completed", output="done")
        app.dependency_overrides[get_auth_context] = lambda: tenant_ctx

        resp = client.get(f"/api/v1/tasks/{TASK_ID}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(TASK_ID)
        assert body["status"] == "completed"
        assert body["output"] == "done"

    def test_not_found_returns_404(self, app, client: TestClient, tenant_ctx, mock_pool) -> None:
        _pool, conn = mock_pool
        conn.fetchrow.return_value = None
        app.dependency_overrides[get_auth_context] = lambda: tenant_ctx

        resp = client.get(f"/api/v1/tasks/{uuid4()}")

        assert resp.status_code == 404


class TestListTasks:
    def test_returns_task_list(self, app, client: TestClient, tenant_ctx, mock_pool) -> None:
        _pool, conn = mock_pool
        conn.fetch.return_value = [
            _task_row(task_id=uuid4()),
            _task_row(task_id=uuid4()),
        ]
        app.dependency_overrides[get_auth_context] = lambda: tenant_ctx

        resp = client.get("/api/v1/tasks")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2

    def test_empty_list(self, app, client: TestClient, tenant_ctx, mock_pool) -> None:
        _pool, conn = mock_pool
        conn.fetch.return_value = []
        app.dependency_overrides[get_auth_context] = lambda: tenant_ctx

        resp = client.get("/api/v1/tasks")

        assert resp.status_code == 200
        assert resp.json() == []
