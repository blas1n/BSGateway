"""Tests for preset system: templates, apply service, feedback.

TDD: Tests written FIRST.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bsgateway.presets.models import (
    ModelMapping,
)
from bsgateway.presets.registry import PresetRegistry, get_builtin_presets
from bsgateway.core.sql_loader import NamedSqlLoader
from bsgateway.presets.repository import FeedbackRepository
from bsgateway.presets.service import PresetService
from bsgateway.tests.conftest import MockTransaction, make_mock_pool


class TestPresetRegistry:
    def test_builtin_presets_exist(self):
        presets = get_builtin_presets()
        names = {p.name for p in presets}
        assert "coding-assistant" in names
        assert "customer-support" in names
        assert "translation-summary" in names
        assert "general" in names

    def test_registry_get_by_name(self):
        registry = PresetRegistry()
        preset = registry.get("coding-assistant")
        assert preset is not None
        assert preset.name == "coding-assistant"
        assert len(preset.intents) > 0
        assert len(preset.rules) > 0

    def test_registry_get_unknown(self):
        registry = PresetRegistry()
        assert registry.get("nonexistent") is None

    def test_registry_list_all(self):
        registry = PresetRegistry()
        all_presets = registry.list_all()
        assert len(all_presets) >= 4

    def test_preset_has_model_levels(self):
        registry = PresetRegistry()
        preset = registry.get("coding-assistant")
        # Rules should reference abstract levels, not concrete models
        for rule in preset.rules:
            if not rule.is_default:
                assert rule.target_level in ("economy", "balanced", "premium")

    def test_preset_default_rule_exists(self):
        registry = PresetRegistry()
        for preset in registry.list_all():
            defaults = [r for r in preset.rules if r.is_default]
            assert len(defaults) == 1, f"{preset.name} must have exactly 1 default rule"


class TestPresetService:
    @pytest.fixture
    def mock_tenant_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.list_models.return_value = [
            {"model_name": "gpt-4o-mini"},
            {"model_name": "gpt-4o"},
            {"model_name": "claude-opus"},
            {"model_name": "claude-sonnet"},
        ]
        return repo

    @pytest.fixture
    def mock_rules_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.list_intents.return_value = []  # No existing intents (idempotency check)

        # Mock _pool for transactional apply_preset
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            side_effect=lambda *args, **kwargs: {
                "id": uuid4(),
                "tenant_id": uuid4(),
                "name": "test",
                "priority": 0,
                "is_active": True,
                "is_default": False,
                "target_model": "gpt-4o",
                "description": "",
                "threshold": 0.7,
                "text": "example",
                "intent_id": uuid4(),
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )

        @asynccontextmanager
        async def mock_transaction():
            yield

        mock_conn.transaction = mock_transaction

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        repo._pool = MagicMock()
        repo._pool.acquire = mock_acquire

        # Mock _sql for named queries
        mock_sql = MagicMock()
        mock_sql.query = lambda name: f"-- mock query: {name}"
        repo._sql = mock_sql

        return repo

    async def test_apply_preset(
        self,
        mock_rules_repo: AsyncMock,
        mock_tenant_repo: AsyncMock,
    ):
        service = PresetService(mock_rules_repo, mock_tenant_repo)
        tid = uuid4()

        mapping = ModelMapping(
            economy="gpt-4o-mini",
            balanced="gpt-4o",
            premium="claude-opus",
        )

        result = await service.apply_preset(
            tenant_id=tid,
            preset_name="coding-assistant",
            model_mapping=mapping,
        )

        assert result.preset_name == "coding-assistant"
        assert result.rules_created > 0
        assert result.intents_created > 0

    async def test_apply_preset_unknown(
        self,
        mock_rules_repo: AsyncMock,
        mock_tenant_repo: AsyncMock,
    ):
        service = PresetService(mock_rules_repo, mock_tenant_repo)
        with pytest.raises(ValueError, match="Unknown preset"):
            await service.apply_preset(
                tenant_id=uuid4(),
                preset_name="nonexistent",
                model_mapping=ModelMapping(
                    economy="a",
                    balanced="b",
                    premium="c",
                ),
            )

    async def test_apply_preset_idempotency(
        self,
        mock_rules_repo: AsyncMock,
        mock_tenant_repo: AsyncMock,
    ):
        """Applying the same preset twice should fail with a clear error."""
        mock_rules_repo.list_intents.return_value = [
            {"name": "code_review"},  # Existing intent from prior apply
        ]
        service = PresetService(mock_rules_repo, mock_tenant_repo)
        with pytest.raises(ValueError, match="already applied"):
            await service.apply_preset(
                tenant_id=uuid4(),
                preset_name="coding-assistant",
                model_mapping=ModelMapping(
                    economy="gpt-4o-mini",
                    balanced="gpt-4o",
                    premium="claude-opus",
                ),
            )


class TestFeedbackModels:
    def test_feedback_schema(self):
        from bsgateway.presets.schemas import FeedbackCreate

        fb = FeedbackCreate(
            routing_id="test-routing-id",
            rating=4,
            comment="Good response",
        )
        assert fb.rating == 4
        assert fb.routing_id == "test-routing-id"

    def test_feedback_rating_range(self):
        from bsgateway.presets.schemas import FeedbackCreate

        with pytest.raises(Exception):
            FeedbackCreate(routing_id="x", rating=6)

        with pytest.raises(Exception):
            FeedbackCreate(routing_id="x", rating=0)


class TestFeedbackSqlLoader:
    def test_schema_loads(self):
        loader = NamedSqlLoader("feedback_schema.sql", "feedback_queries.sql")
        schema = loader.schema()
        assert "routing_feedback" in schema

    def test_query_loads(self):
        loader = NamedSqlLoader("feedback_schema.sql", "feedback_queries.sql")
        q = loader.query("insert_feedback")
        assert "INSERT" in q

    def test_query_list_feedback(self):
        loader = NamedSqlLoader("feedback_schema.sql", "feedback_queries.sql")
        q = loader.query("list_feedback")
        assert "SELECT" in q

    def test_query_get_feedback_stats(self):
        loader = NamedSqlLoader("feedback_schema.sql", "feedback_queries.sql")
        q = loader.query("get_feedback_stats")
        assert "AVG" in q


class TestFeedbackRepository:
    @pytest.fixture
    def pool_and_conn(self):
        pool, conn = make_mock_pool()
        return pool, conn

    async def test_init_schema(self, pool_and_conn):
        pool, conn = pool_and_conn
        conn.execute = AsyncMock()
        # transaction() needs to be a sync call returning an async context manager
        conn.transaction = MagicMock(return_value=MockTransaction())
        repo = FeedbackRepository(pool)
        await repo.init_schema()
        assert conn.execute.call_count > 0

    async def test_create_feedback(self, pool_and_conn):
        pool, conn = pool_and_conn
        tid = uuid4()
        expected = {
            "id": uuid4(),
            "tenant_id": tid,
            "routing_id": "route-1",
            "rating": 4,
            "comment": "good",
            "created_at": datetime.now(UTC),
        }
        conn.fetchrow = AsyncMock(return_value=expected)
        repo = FeedbackRepository(pool)
        result = await repo.create_feedback(tid, "route-1", 4, "good")
        assert result == expected
        conn.fetchrow.assert_called_once()

    async def test_list_feedback(self, pool_and_conn):
        pool, conn = pool_and_conn
        tid = uuid4()
        rows = [
            {
                "id": uuid4(),
                "tenant_id": tid,
                "routing_id": "r1",
                "rating": 3,
                "comment": "",
                "created_at": datetime.now(UTC),
            }
        ]
        conn.fetch = AsyncMock(return_value=rows)
        repo = FeedbackRepository(pool)
        result = await repo.list_feedback(tid, limit=10, offset=0)
        assert len(result) == 1
        conn.fetch.assert_called_once()

    async def test_get_stats(self, pool_and_conn):
        pool, conn = pool_and_conn
        tid = uuid4()
        stats = {"total": 10, "avg_rating": 3.5, "positive": 6, "negative": 2}
        conn.fetchrow = AsyncMock(return_value=stats)
        repo = FeedbackRepository(pool)
        result = await repo.get_stats(tid)
        assert result["total"] == 10
        assert result["avg_rating"] == 3.5
        conn.fetchrow.assert_called_once()
