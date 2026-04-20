"""Tests for RedisStreamManager: publish, consume, acknowledge."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from bsgateway.streams import RedisStreamManager


@pytest.fixture
def mock_redis() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def stream_manager(mock_redis: AsyncMock) -> RedisStreamManager:
    return RedisStreamManager(mock_redis)


class TestPublish:
    async def test_publish_flattens_dict_values(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.xadd.return_value = b"1234-0"
        data = {"key": "value", "nested": {"a": 1}, "items": [1, 2]}

        result = await stream_manager.publish("mystream", data)

        mock_redis.xadd.assert_awaited_once()
        call_args = mock_redis.xadd.call_args
        flat = call_args[0][1]
        assert flat["key"] == "value"
        assert flat["nested"] == json.dumps({"a": 1})
        assert flat["items"] == json.dumps([1, 2])
        assert result == "1234-0"

    async def test_publish_converts_non_string_keys(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.xadd.return_value = b"5678-0"
        data = {42: "val"}

        await stream_manager.publish("s", data)

        flat = mock_redis.xadd.call_args[0][1]
        assert "42" in flat

    async def test_publish_returns_str_when_redis_returns_str(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.xadd.return_value = "9999-0"

        result = await stream_manager.publish("s", {"a": "b"})

        assert result == "9999-0"


class TestConsume:
    async def test_consume_creates_group_and_reads(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.xgroup_create = AsyncMock()
        mock_redis.xreadgroup.return_value = [
            (
                b"mystream",
                [
                    (b"111-0", {b"task_id": b"abc", b"count": b"5"}),
                ],
            ),
        ]

        results = await stream_manager.consume("mystream", "grp", "consumer-0", count=1, block=500)

        mock_redis.xgroup_create.assert_awaited_once_with("mystream", "grp", id="0", mkstream=True)
        mock_redis.xreadgroup.assert_awaited_once()
        assert len(results) == 1
        assert results[0]["task_id"] == "abc"
        assert results[0]["count"] == 5  # parsed as int via json.loads
        assert results[0]["_message_id"] == "111-0"

    async def test_consume_returns_empty_when_no_messages(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.xgroup_create = AsyncMock()
        mock_redis.xreadgroup.return_value = []

        results = await stream_manager.consume("s", "g", "c")

        assert results == []

    async def test_consume_ignores_existing_group_error(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.xgroup_create = AsyncMock(side_effect=Exception("BUSYGROUP already exists"))
        mock_redis.xreadgroup.return_value = []

        results = await stream_manager.consume("s", "g", "c")

        assert results == []

    async def test_consume_parses_json_nested_values(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.xgroup_create = AsyncMock()
        nested = json.dumps({"x": 1})
        mock_redis.xreadgroup.return_value = [
            (b"s", [(b"1-0", {b"data": nested.encode()})]),
        ]

        results = await stream_manager.consume("s", "g", "c")

        assert results[0]["data"] == {"x": 1}

    async def test_consume_keeps_non_json_as_string(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.xgroup_create = AsyncMock()
        mock_redis.xreadgroup.return_value = [
            (b"s", [(b"1-0", {b"name": b"plain-text"})]),
        ]

        results = await stream_manager.consume("s", "g", "c")

        assert results[0]["name"] == "plain-text"


class TestAcknowledge:
    async def test_acknowledge_calls_xack(
        self, stream_manager: RedisStreamManager, mock_redis: AsyncMock
    ) -> None:
        await stream_manager.acknowledge("mystream", "grp", "111-0")

        mock_redis.xack.assert_awaited_once_with("mystream", "grp", "111-0")
