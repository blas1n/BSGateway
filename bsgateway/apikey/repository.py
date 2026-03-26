from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

if TYPE_CHECKING:
    import asyncpg

logger = structlog.get_logger(__name__)


class _SqlLoader:
    """Load named queries from apikey_queries.sql."""

    def __init__(self) -> None:
        self._sql_dir = Path(__file__).parent.parent / "routing" / "sql"
        self._queries: dict[str, str] = {}

    def schema(self) -> str:
        return (self._sql_dir / "apikey_schema.sql").read_text()

    def query(self, name: str) -> str:
        if not self._queries:
            self._parse_queries()
        return self._queries[name]

    def _parse_queries(self) -> None:
        content = (self._sql_dir / "apikey_queries.sql").read_text()
        current_name: str | None = None
        current_lines: list[str] = []
        for line in content.splitlines():
            if line.strip().startswith("-- name:"):
                if current_name:
                    self._queries[current_name] = "\n".join(current_lines).strip()
                current_name = line.strip().split("-- name:")[1].strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_name:
            self._queries[current_name] = "\n".join(current_lines).strip()


_sql = _SqlLoader()


class ApiKeyRepository:
    """Database access for API keys."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def init_schema(self) -> None:
        schema = _sql.schema()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for statement in schema.split(";"):
                    statement = statement.strip()
                    if statement:
                        await conn.execute(statement)

    async def create(
        self,
        tenant_id: UUID,
        name: str,
        key_hash: str,
        key_prefix: str,
        scopes: list[str],
        expires_at: str | None = None,
    ) -> asyncpg.Record:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                _sql.query("insert_api_key"),
                tenant_id,
                name,
                key_hash,
                key_prefix,
                json.dumps(scopes),
                expires_at,
            )

    async def get_by_hash(self, key_hash: str) -> asyncpg.Record | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(_sql.query("get_api_key_by_hash"), key_hash)

    async def list_by_tenant(self, tenant_id: UUID) -> list[asyncpg.Record]:
        async with self._pool.acquire() as conn:
            return await conn.fetch(_sql.query("list_api_keys_by_tenant"), tenant_id)

    async def revoke(self, key_id: UUID, tenant_id: UUID) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_sql.query("revoke_api_key"), key_id, tenant_id)

    async def touch_last_used(self, key_id: UUID) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_sql.query("touch_last_used"), key_id)
