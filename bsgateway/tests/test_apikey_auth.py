"""Tests for dual auth middleware (JWT or API Key)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from bsgateway.api.app import create_app
from bsgateway.tests.conftest import make_mock_pool

ENCRYPTION_KEY_HEX = os.urandom(32).hex()


@pytest.fixture
def mock_pool():
    pool, _conn = make_mock_pool()
    return pool


def _make_app(mock_pool):
    """Create app WITHOUT auth override (test real auth flow)."""
    app = create_app()
    app.state.db_pool = mock_pool
    app.state.encryption_key = bytes.fromhex(ENCRYPTION_KEY_HEX)
    app.state.redis = None
    app.state.auth_provider = AsyncMock()
    return app


class TestApiKeyAuth:
    def test_apikey_auth_resolves_tenant(self, mock_pool):
        """Bearer bsg_live_xxx authenticates via API key path."""
        app = _make_app(mock_pool)
        client = TestClient(app, raise_server_exceptions=False)
        tid = uuid4()

        from bsgateway.apikey.models import ValidatedKey

        validated = ValidatedKey(
            key_id=uuid4(),
            tenant_id=tid,
            scopes=["chat"],
        )

        with (
            patch(
                "bsgateway.apikey.service.ApiKeyService.validate_key",
                new_callable=AsyncMock,
                return_value=validated,
            ),
            patch(
                "bsgateway.tenant.repository.TenantRepository.get_tenant",
                new_callable=AsyncMock,
                return_value={
                    "id": tid,
                    "name": "Test",
                    "slug": "test",
                    "is_active": True,
                    "settings": "{}",
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            ),
        ):
            resp = client.get(
                f"/api/v1/tenants/{tid}/api-keys",
                headers={"Authorization": "Bearer bsg_live_" + "a" * 64},
            )

        # Should not get 401 — key was validated
        assert resp.status_code != 401

    def test_invalid_apikey_returns_401(self, mock_pool):
        """Invalid API key returns 401."""
        app = _make_app(mock_pool)
        client = TestClient(app, raise_server_exceptions=False)

        with patch(
            "bsgateway.apikey.service.ApiKeyService.validate_key",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get(
                f"/api/v1/tenants/{uuid4()}/api-keys",
                headers={"Authorization": "Bearer bsg_live_" + "x" * 64},
            )

        assert resp.status_code == 401

    def test_jwt_auth_still_works(self, mock_pool):
        """JWT tokens still go through the existing JWT path."""
        app = _make_app(mock_pool)
        client = TestClient(app, raise_server_exceptions=False)

        # Non-bsg_live_ token → JWT path → auth_provider.verify_token
        from bsvibe_auth import AuthError

        app.state.auth_provider.verify_token = AsyncMock(
            side_effect=AuthError("Invalid token"),
        )

        resp = client.get(
            f"/api/v1/tenants/{uuid4()}/api-keys",
            headers={"Authorization": "Bearer eyJhbGciOiJFUzI1NiJ9.fake.token"},
        )

        # JWT validation was attempted (and failed)
        assert resp.status_code == 401
        app.state.auth_provider.verify_token.assert_called_once()

    def test_no_auth_header_returns_401(self, mock_pool):
        """Missing Authorization header returns 401."""
        app = _make_app(mock_pool)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(f"/api/v1/tenants/{uuid4()}/api-keys")
        assert resp.status_code == 401
