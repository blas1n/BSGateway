"""Redis Streams abstraction layer for task dispatch."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisStreamManager:
    """Thin wrapper around Redis Streams for publish/consume/acknowledge."""

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    async def publish(self, stream: str, data: dict) -> str:
        """Publish a message to a stream. Returns the message ID."""
        flat: dict[str, str] = {
            str(k): json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in data.items()
        }
        msg_id: bytes = await self.redis.xadd(stream, flat)  # type: ignore[arg-type]
        return msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)

    async def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 1,
        block: int = 1000,
    ) -> list[dict]:
        """Consume messages from a consumer group."""
        # Ensure consumer group exists
        try:
            await self.redis.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception:
            pass  # Group already exists

        messages = await self.redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block,
        )
        results: list[dict] = []
        if messages:
            for _stream_name, stream_messages in messages:
                for message_id, data in stream_messages:
                    parsed: dict = {}
                    for k, v in data.items():
                        key = k.decode() if isinstance(k, bytes) else k
                        val = v.decode() if isinstance(v, bytes) else v
                        try:
                            parsed[key] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            parsed[key] = val
                    mid = message_id.decode() if isinstance(message_id, bytes) else message_id
                    parsed["_message_id"] = mid
                    results.append(parsed)
        return results

    async def acknowledge(self, stream: str, group: str, message_id: str) -> None:
        """Acknowledge message processing completion."""
        await self.redis.xack(stream, group, message_id)
