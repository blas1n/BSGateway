from __future__ import annotations

from uuid import UUID

import asyncpg
import structlog

from bsgateway.core.sql_loader import NamedSqlLoader

logger = structlog.get_logger(__name__)

sql = NamedSqlLoader("feedback_schema.sql", "feedback_queries.sql")


class FeedbackRepository:
    """Database access for routing feedback."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def init_schema(self) -> None:
        schema = sql.schema()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for statement in schema.split(";"):
                    statement = statement.strip()
                    if statement:
                        await conn.execute(statement)

    async def create_feedback(
        self,
        tenant_id: UUID,
        routing_id: str,
        rating: int,
        comment: str = "",
    ) -> asyncpg.Record:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                sql.query("insert_feedback"),
                tenant_id,
                routing_id,
                rating,
                comment,
            )

    async def list_feedback(
        self,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[asyncpg.Record]:
        async with self._pool.acquire() as conn:
            return await conn.fetch(
                sql.query("list_feedback"),
                tenant_id,
                limit,
                offset,
            )

    async def get_stats(self, tenant_id: UUID) -> asyncpg.Record | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                sql.query("get_feedback_stats"),
                tenant_id,
            )
