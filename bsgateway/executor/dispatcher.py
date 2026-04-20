"""Worker dispatcher — Redis Streams based task dispatch to remote workers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog

from bsgateway.streams import RedisStreamManager

logger = structlog.get_logger(__name__)

WORKER_STREAM_PREFIX = "tasks:worker:"


class WorkerDispatcher:
    """Dispatches executor tasks to remote workers via Redis Streams."""

    def __init__(self, stream_manager: RedisStreamManager) -> None:
        self._stream = stream_manager

    def _worker_stream(self, worker_id: UUID) -> str:
        return f"{WORKER_STREAM_PREFIX}{worker_id}"

    async def dispatch_task(
        self,
        worker_id: UUID,
        task_id: UUID,
        executor_type: str,
        prompt: str,
    ) -> str:
        """Publish a task to a worker's dedicated stream."""
        data = {
            "task_id": str(task_id),
            "executor_type": executor_type,
            "prompt": prompt,
            "action": "execute",
            "dispatched_at": datetime.now(UTC).isoformat(),
        }
        msg_id = await self._stream.publish(self._worker_stream(worker_id), data)
        logger.info(
            "task_dispatched",
            worker_id=str(worker_id),
            task_id=str(task_id),
            executor_type=executor_type,
        )
        return msg_id
