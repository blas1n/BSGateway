"""Tests for the Redis cache layer."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from bsgateway.core.cache import (
    CACHE_TTL_RULES,
    CacheManager,
    _CacheEncoder,
    cache_key_models,
    cache_key_rules,
    cache_key_tenant_config,
    cache_key_usage,
)


class TestCacheEncoder:
    """Tests for the JSON encoder that handles UUID/datetime."""

    def test_uuid_serialization(self):
        uid = uuid4()
        result = json.dumps({"id": uid}, cls=_CacheEncoder)
        assert str(uid) in result

    def test_datetime_serialization(self):
        from datetime import datetime

        dt = datetime(2026, 1, 1, 12, 0, 0)
        result = json.dumps({"ts": dt}, cls=_CacheEncoder)
        assert "2026-01-01" in result

    def test_regular_types_pass_through(self):
        result = json.dumps({"name": "test", "count": 42}, cls=_CacheEncoder)
        parsed = json.loads(result)
        assert parsed == {"name": "test", "count": 42}

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            json.dumps({"obj": object()}, cls=_CacheEncoder)


class TestCacheManager:
    """Unit tests for CacheManager."""

    def _make_manager(self, redis: AsyncMock | None = None) -> CacheManager:
        return CacheManager(redis or AsyncMock())

    @pytest.mark.asyncio
    async def test_get_returns_deserialized_value(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=json.dumps({"key": "value"}).encode())
        mgr = self._make_manager(redis)

        result = await mgr.get("test-key")
        assert result == {"key": "value"}
        redis.get.assert_awaited_once_with("test-key")

    @pytest.mark.asyncio
    async def test_get_returns_none_on_miss(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        mgr = self._make_manager(redis)

        result = await mgr.get("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_on_error(self):
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=ConnectionError("down"))
        mgr = self._make_manager(redis)

        result = await mgr.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_without_ttl(self):
        redis = AsyncMock()
        redis.set = AsyncMock()
        mgr = self._make_manager(redis)

        result = await mgr.set("k", {"v": 1})
        assert result is True
        redis.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        redis = AsyncMock()
        redis.setex = AsyncMock()
        mgr = self._make_manager(redis)

        ttl = timedelta(minutes=5)
        result = await mgr.set("k", "v", ttl=ttl)
        assert result is True
        redis.setex.assert_awaited_once_with("k", 300, json.dumps("v"))

    @pytest.mark.asyncio
    async def test_set_returns_false_on_error(self):
        redis = AsyncMock()
        redis.set = AsyncMock(side_effect=ConnectionError("down"))
        mgr = self._make_manager(redis)

        result = await mgr.set("k", "v")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_single_key(self):
        redis = AsyncMock()
        redis.delete = AsyncMock()
        mgr = self._make_manager(redis)

        result = await mgr.delete("k")
        assert result is True
        redis.delete.assert_awaited_once_with("k")

    @pytest.mark.asyncio
    async def test_delete_multiple_keys(self):
        redis = AsyncMock()
        redis.delete = AsyncMock()
        mgr = self._make_manager(redis)

        result = await mgr.delete(["a", "b", "c"])
        assert result is True
        redis.delete.assert_awaited_once_with("a", "b", "c")

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(self):
        redis = AsyncMock()
        redis.delete = AsyncMock(side_effect=ConnectionError("down"))
        mgr = self._make_manager(redis)

        result = await mgr.delete("k")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true(self):
        redis = AsyncMock()
        redis.exists = AsyncMock(return_value=1)
        mgr = self._make_manager(redis)

        assert await mgr.exists("k") is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_on_miss(self):
        redis = AsyncMock()
        redis.exists = AsyncMock(return_value=0)
        mgr = self._make_manager(redis)

        assert await mgr.exists("k") is False

    @pytest.mark.asyncio
    async def test_exists_returns_false_on_error(self):
        redis = AsyncMock()
        redis.exists = AsyncMock(side_effect=ConnectionError("down"))
        mgr = self._make_manager(redis)

        assert await mgr.exists("k") is False

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_hit(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=json.dumps({"cached": True}).encode())
        mgr = self._make_manager(redis)

        fetcher = AsyncMock(return_value={"fresh": True})
        result = await mgr.get_or_fetch("k", fetcher)
        assert result == {"cached": True}
        fetcher.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_miss_async_fetcher(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        mgr = self._make_manager(redis)

        fetcher = AsyncMock(return_value={"fresh": True})
        result = await mgr.get_or_fetch("k", fetcher, ttl=timedelta(minutes=5))
        assert result == {"fresh": True}
        fetcher.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_miss_sync_fetcher(self):
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        mgr = self._make_manager(redis)

        def sync_fetcher():
            return {"sync": True}

        result = await mgr.get_or_fetch("k", sync_fetcher)
        assert result == {"sync": True}

    @pytest.mark.asyncio
    async def test_increment(self):
        redis = AsyncMock()
        redis.incrby = AsyncMock(return_value=5)
        mgr = self._make_manager(redis)

        result = await mgr.increment("counter", 3)
        assert result == 5
        redis.incrby.assert_awaited_once_with("counter", 3)

    @pytest.mark.asyncio
    async def test_increment_returns_zero_on_error(self):
        redis = AsyncMock()
        redis.incrby = AsyncMock(side_effect=ConnectionError("down"))
        mgr = self._make_manager(redis)

        result = await mgr.increment("counter")
        assert result == 0


class TestCacheKeyFunctions:
    """Tests for cache key generation."""

    def test_cache_key_rules(self):
        assert cache_key_rules("t1") == "cache:rules:t1"

    def test_cache_key_models(self):
        assert cache_key_models("t1") == "cache:models:t1"

    def test_cache_key_usage(self):
        assert cache_key_usage("t1", "2026-03") == "cache:usage:t1:2026-03"

    def test_cache_key_tenant_config(self):
        assert cache_key_tenant_config("t1") == "cache:tenant_config:t1"

    def test_cache_ttl_rules_is_timedelta(self):
        assert isinstance(CACHE_TTL_RULES, timedelta)
