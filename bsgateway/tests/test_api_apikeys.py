"""Tests for API key management endpoints."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from bsgateway.api.app import create_app
from bsgateway.api.deps import get_auth_context
from bsgateway.tests.conftest import make_gateway_auth_context, make_mock_pool

ENCRYPTION_KEY_HEX = os.urandom(32).hex()
ADMIN_TENANT_ID = uuid4()


@pytest.fixture
def mock_pool():
    pool, _conn = make_mock_pool()
    return pool


@pytest.fixture
def app(mock_pool):
    app = create_app()
    app.state.db_pool = mock_pool
    app.state.encryption_key = bytes.fromhex(ENCRYPTION_KEY_HEX)
    app.state.redis = None
    admin_ctx = make_gateway_auth_context(tenant_id=ADMIN_TENANT_ID, is_admin=True)
    app.dependency_overrides[get_auth_context] = lambda: admin_ctx
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def member_app(mock_pool):
    """App with non-admin member auth."""
    app = create_app()
    app.state.db_pool = mock_pool
    app.state.encryption_key = bytes.fromhex(ENCRYPTION_KEY_HEX)
    app.state.redis = None
    member_ctx = make_gateway_auth_context(tenant_id=ADMIN_TENANT_ID, is_admin=False)
    app.dependency_overrides[get_auth_context] = lambda: member_ctx
    return app


class TestCreateApiKey:
    def test_create_key_returns_201(self, client: TestClient):
        tid = ADMIN_TENANT_ID
        now = datetime.now(UTC)
        key_id = uuid4()

        with patch(
            "bsgateway.apikey.service.ApiKeyService.create_key",
            new_callable=AsyncMock,
        ) as mock_create:
            from bsgateway.apikey.models import ApiKeyCreated

            mock_create.return_value = ApiKeyCreated(
                id=key_id,
                tenant_id=tid,
                name="my-key",
                key_prefix="bsg_live_abc",
                raw_key="bsg_live_" + "a" * 64,
                scopes=["chat"],
                created_at=now,
            )
            resp = client.post(
                f"/api/v1/tenants/{tid}/api-keys",
                json={"name": "my-key"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "my-key"
        assert "raw_key" in data
        assert data["raw_key"].startswith("bsg_live_")

    def test_create_key_missing_name_returns_422(self, client: TestClient):
        resp = client.post(
            f"/api/v1/tenants/{ADMIN_TENANT_ID}/api-keys",
            json={},
        )
        assert resp.status_code == 422


class TestListApiKeys:
    def test_list_keys(self, client: TestClient):
        tid = ADMIN_TENANT_ID
        now = datetime.now(UTC)

        with patch(
            "bsgateway.apikey.service.ApiKeyService.list_keys",
            new_callable=AsyncMock,
        ) as mock_list:
            from bsgateway.apikey.models import ApiKeyInfo

            mock_list.return_value = [
                ApiKeyInfo(
                    id=uuid4(),
                    tenant_id=tid,
                    name="key-1",
                    key_prefix="bsg_live_abc",
                    scopes=["chat"],
                    is_active=True,
                    expires_at=None,
                    last_used_at=None,
                    created_at=now,
                ),
            ]
            resp = client.get(f"/api/v1/tenants/{tid}/api-keys")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "raw_key" not in data[0]
        assert "key_hash" not in data[0]


class TestRevokeApiKey:
    def test_revoke_key_returns_204(self, client: TestClient):
        tid = ADMIN_TENANT_ID
        kid = uuid4()

        with patch(
            "bsgateway.apikey.service.ApiKeyService.revoke_key",
            new_callable=AsyncMock,
        ):
            resp = client.delete(f"/api/v1/tenants/{tid}/api-keys/{kid}")

        assert resp.status_code == 204


class TestCrossTenantAccess:
    def test_member_cannot_access_other_tenant_keys(self, mock_pool):
        """Non-admin cannot list another tenant's keys."""
        own_tid = uuid4()
        other_tid = uuid4()
        app = create_app()
        app.state.db_pool = mock_pool
        app.state.encryption_key = bytes.fromhex(ENCRYPTION_KEY_HEX)
        app.state.redis = None
        member_ctx = make_gateway_auth_context(tenant_id=own_tid, is_admin=False)
        app.dependency_overrides[get_auth_context] = lambda: member_ctx
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(f"/api/v1/tenants/{other_tid}/api-keys")
        assert resp.status_code == 403
