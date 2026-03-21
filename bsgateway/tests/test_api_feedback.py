"""Tests for the feedback API endpoints."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from bsgateway.api.app import create_app
from bsgateway.core.security import hash_api_key

SUPERADMIN_KEY = "test-superadmin-key"
ENCRYPTION_KEY_HEX = os.urandom(32).hex()
TENANT_ID = uuid4()


@pytest.fixture
def mock_pool() -> AsyncMock:
    pool = AsyncMock()
    pool._closed = False
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


@pytest.fixture
def app(mock_pool: AsyncMock):
    app = create_app()
    app.state.db_pool = mock_pool
    app.state.encryption_key = bytes.fromhex(ENCRYPTION_KEY_HEX)
    app.state.superadmin_key_hash = hash_api_key(SUPERADMIN_KEY)
    app.state.jwt_secret = "test-jwt-secret"
    app.state.redis = None
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_headers() -> dict:
    return {"Authorization": f"Bearer {SUPERADMIN_KEY}"}


def _make_feedback_row(
    tenant_id=None,
    routing_id="route-123",
    rating=5,
    comment="Great routing",
):
    return {
        "id": uuid4(),
        "tenant_id": tenant_id or TENANT_ID,
        "routing_id": routing_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now(UTC),
    }


class TestFeedbackAPI:
    def test_submit_feedback(self, client: TestClient, admin_headers: dict):
        row = _make_feedback_row(tenant_id=TENANT_ID)
        with patch(
            "bsgateway.presets.repository.FeedbackRepository.create_feedback",
            new_callable=AsyncMock,
            return_value=row,
        ):
            resp = client.post(
                f"/api/v1/tenants/{TENANT_ID}/feedback",
                json={
                    "routing_id": "route-123",
                    "rating": 5,
                    "comment": "Great routing",
                },
                headers=admin_headers,
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["routing_id"] == "route-123"
        assert data["rating"] == 5
        assert data["comment"] == "Great routing"
        assert data["tenant_id"] == str(TENANT_ID)

    def test_list_feedback(self, client: TestClient, admin_headers: dict):
        rows = [
            _make_feedback_row(tenant_id=TENANT_ID),
            _make_feedback_row(tenant_id=TENANT_ID, rating=3, comment="OK"),
        ]
        with patch(
            "bsgateway.presets.repository.FeedbackRepository.list_feedback",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            resp = client.get(
                f"/api/v1/tenants/{TENANT_ID}/feedback",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_feedback_with_pagination(self, client: TestClient, admin_headers: dict):
        rows = [_make_feedback_row(tenant_id=TENANT_ID)]
        with patch(
            "bsgateway.presets.repository.FeedbackRepository.list_feedback",
            new_callable=AsyncMock,
            return_value=rows,
        ) as mock_list:
            resp = client.get(
                f"/api/v1/tenants/{TENANT_ID}/feedback?limit=10&offset=20",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        mock_list.assert_called_once_with(TENANT_ID, 10, 20)

    def test_submit_feedback_missing_fields(self, client: TestClient, admin_headers: dict):
        resp = client.post(
            f"/api/v1/tenants/{TENANT_ID}/feedback",
            json={"comment": "No rating or routing_id"},
            headers=admin_headers,
        )
        assert resp.status_code == 422
