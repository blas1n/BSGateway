"""Tests for the development seed data module."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bsgateway.core.seed import DEV_TENANT_SLUG, seed_dev_data

ENCRYPTION_KEY = bytes.fromhex(os.urandom(32).hex())


class _MockAcquire:
    """Mock for asyncpg pool.acquire() that supports async with."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class _MockTx:
    """Mock for conn.transaction() that supports async with."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class TestSeedDevData:
    """Tests for seed_dev_data()."""

    def _make_pool(self, conn: AsyncMock) -> AsyncMock:
        pool = AsyncMock()
        pool.acquire = MagicMock(return_value=_MockAcquire(conn))
        conn.transaction = MagicMock(return_value=_MockTx())
        return pool

    @pytest.mark.asyncio
    @patch("bsgateway.core.seed.TenantRepository")
    async def test_skips_if_tenant_exists(self, mock_repo_cls):
        repo = AsyncMock()
        repo.get_tenant_by_slug = AsyncMock(return_value={"id": "existing"})
        mock_repo_cls.return_value = repo

        pool = AsyncMock()
        await seed_dev_data(pool, ENCRYPTION_KEY)

        repo.get_tenant_by_slug.assert_awaited_once_with(DEV_TENANT_SLUG)
        pool.acquire.assert_not_called()

    @pytest.mark.asyncio
    @patch("bsgateway.core.seed.encrypt_value", return_value="encrypted")
    @patch("bsgateway.core.seed.hash_api_key", return_value="hashed")
    @patch("bsgateway.core.seed.TenantRepository")
    async def test_creates_tenant_and_models(self, mock_repo_cls, mock_hash, mock_encrypt):
        repo = AsyncMock()
        repo.get_tenant_by_slug = AsyncMock(return_value=None)
        mock_repo_cls.return_value = repo

        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"id": "new-tenant-id"})
        conn.execute = AsyncMock()
        pool = self._make_pool(conn)

        await seed_dev_data(pool, ENCRYPTION_KEY)

        # Tenant created
        assert conn.fetchrow.await_count == 1
        # API key + 3 models + 1 rule = 5 executions
        assert conn.execute.await_count == 5

    @pytest.mark.asyncio
    @patch("bsgateway.core.seed.encrypt_value", return_value="encrypted")
    @patch("bsgateway.core.seed.hash_api_key", return_value="hashed")
    @patch("bsgateway.core.seed.TenantRepository")
    async def test_skips_encryption_if_no_key(self, mock_repo_cls, mock_hash, mock_encrypt):
        repo = AsyncMock()
        repo.get_tenant_by_slug = AsyncMock(return_value=None)
        mock_repo_cls.return_value = repo

        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"id": "new-tenant-id"})
        conn.execute = AsyncMock()
        pool = self._make_pool(conn)

        await seed_dev_data(pool, b"")

        mock_encrypt.assert_not_called()

    @pytest.mark.asyncio
    @patch("bsgateway.core.seed.encrypt_value", return_value="encrypted")
    @patch("bsgateway.core.seed.hash_api_key", return_value="hashed")
    @patch("bsgateway.core.seed.TenantRepository")
    async def test_does_not_log_full_api_key(self, mock_repo_cls, mock_hash, mock_encrypt):
        """Verify the full API key is not logged (security)."""
        repo = AsyncMock()
        repo.get_tenant_by_slug = AsyncMock(return_value=None)
        mock_repo_cls.return_value = repo

        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"id": "new-tenant-id"})
        conn.execute = AsyncMock()
        pool = self._make_pool(conn)

        with patch("bsgateway.core.seed.logger") as mock_logger:
            await seed_dev_data(pool, ENCRYPTION_KEY)

            # Verify the full key is not in the log call
            call_kwargs = mock_logger.info.call_args_list[-1].kwargs
            assert "api_key" not in call_kwargs
            assert "api_key_prefix" in call_kwargs
            assert call_kwargs["api_key_prefix"].endswith("...")
