from __future__ import annotations

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool(database_url: str, min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    """Get or create the shared asyncpg connection pool.

    Reuses a single pool across the application. Call :func:`close_pool`
    during shutdown to release connections.

    TODO: register a connection-level jsonb codec (``conn.set_type_codec(
    'jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog')``
    via ``init=`` callback) so asyncpg returns JSONB columns as Python
    dicts/lists directly. Removes per-query Python-side decoding scattered
    across the codebase (see routers/workers.py list_workers).
    """
    global _pool
    if _pool is None or _pool.is_closing():
        _pool = await asyncpg.create_pool(database_url, min_size=min_size, max_size=max_size)
        logger.info("database_pool_created", min_size=min_size, max_size=max_size)
    return _pool


async def close_pool() -> None:
    """Close the shared connection pool."""
    global _pool
    if _pool is not None and not _pool.is_closing():
        await _pool.close()
        _pool = None
        logger.info("database_pool_closed")


async def execute_schema(pool: asyncpg.Pool, schema_sql: str) -> None:
    """Execute a schema SQL string (multiple statements separated by semicolons)."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            for statement in schema_sql.split(";"):
                statement = statement.strip()
                if statement:
                    await conn.execute(statement)
