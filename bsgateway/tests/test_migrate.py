"""Tests for the database migration runner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunMigrations:
    """Tests for run_migrations()."""

    @pytest.mark.asyncio
    @patch("bsgateway.core.migrate.settings")
    async def test_raises_without_database_url(self, mock_settings):
        mock_settings.collector_database_url = None

        from bsgateway.core.migrate import run_migrations

        with pytest.raises(RuntimeError, match="collector_database_url is required"):
            await run_migrations()

    @pytest.mark.asyncio
    @patch("bsgateway.core.migrate.FeedbackRepository")
    @patch("bsgateway.core.migrate.RulesRepository")
    @patch("bsgateway.core.migrate.TenantRepository")
    @patch("bsgateway.core.migrate.AuditRepository")
    @patch("bsgateway.core.migrate.execute_schema")
    @patch("bsgateway.core.migrate.SqlLoader")
    @patch("bsgateway.core.migrate.asyncpg")
    @patch("bsgateway.core.migrate.settings")
    async def test_applies_all_schemas(
        self,
        mock_settings,
        mock_asyncpg,
        mock_sql_loader,
        mock_exec_schema,
        mock_audit_repo_cls,
        mock_tenant_repo_cls,
        mock_rules_repo_cls,
        mock_feedback_repo_cls,
    ):
        mock_settings.collector_database_url = "postgresql://test"

        pool = AsyncMock()
        mock_asyncpg.create_pool = AsyncMock(return_value=pool)

        sql_loader = MagicMock()
        sql_loader.schema.return_value = "CREATE TABLE ..."
        mock_sql_loader.return_value = sql_loader

        mock_exec_schema.return_value = None

        for repo_cls in (
            mock_tenant_repo_cls,
            mock_rules_repo_cls,
            mock_feedback_repo_cls,
            mock_audit_repo_cls,
        ):
            repo_cls.return_value.init_schema = AsyncMock()

        from bsgateway.core.migrate import run_migrations

        await run_migrations()

        mock_exec_schema.assert_awaited_once()
        for repo_cls in (
            mock_tenant_repo_cls,
            mock_rules_repo_cls,
            mock_feedback_repo_cls,
            mock_audit_repo_cls,
        ):
            repo_cls.return_value.init_schema.assert_awaited_once()
        pool.close.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("bsgateway.core.migrate.FeedbackRepository")
    @patch("bsgateway.core.migrate.RulesRepository")
    @patch("bsgateway.core.migrate.TenantRepository")
    @patch("bsgateway.core.migrate.AuditRepository")
    @patch("bsgateway.core.migrate.execute_schema")
    @patch("bsgateway.core.migrate.SqlLoader")
    @patch("bsgateway.core.migrate.asyncpg")
    @patch("bsgateway.core.migrate.settings")
    async def test_closes_pool_on_error(
        self,
        mock_settings,
        mock_asyncpg,
        mock_sql_loader,
        mock_exec_schema,
        mock_audit_repo_cls,
        mock_tenant_repo_cls,
        mock_rules_repo_cls,
        mock_feedback_repo_cls,
    ):
        mock_settings.collector_database_url = "postgresql://test"

        pool = AsyncMock()
        mock_asyncpg.create_pool = AsyncMock(return_value=pool)

        mock_exec_schema.side_effect = RuntimeError("schema error")

        from bsgateway.core.migrate import run_migrations

        with pytest.raises(RuntimeError, match="schema error"):
            await run_migrations()

        pool.close.assert_awaited_once()
