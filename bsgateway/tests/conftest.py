"""Shared test fixtures and helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


class MockAcquire:
    """Proper async context manager for mocking pool.acquire()."""

    def __init__(self, conn: AsyncMock) -> None:
        self.conn = conn

    async def __aenter__(self) -> AsyncMock:
        return self.conn

    async def __aexit__(self, *args: object) -> None:
        pass


class MockTransaction:
    """Proper async context manager for mocking conn.transaction()."""

    async def __aenter__(self) -> MockTransaction:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


def make_mock_pool() -> tuple[MagicMock, AsyncMock]:
    """Create a properly mocked asyncpg pool that doesn't trigger RuntimeWarnings.

    Returns:
        Tuple of (pool, conn) where pool is MagicMock and conn is AsyncMock.
    """
    pool = MagicMock()
    pool._closed = False
    conn = AsyncMock()
    conn.transaction.return_value = MockTransaction()
    pool.acquire.return_value = MockAcquire(conn)
    return pool, conn
