"""Worker install token — mint/verify/revoke, stored in tenant settings JSONB."""

from __future__ import annotations

import hashlib
import secrets
from uuid import UUID

import asyncpg

from bsgateway.core.utils import safe_json_loads

# Settings key inside tenants.settings JSONB
_SETTINGS_KEY = "worker_install_token_hash"
_TOKEN_PREFIX = "bsg-"


def hash_install_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_install_token() -> str:
    return f"{_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


async def has_install_token(pool: asyncpg.Pool, tenant_id: UUID) -> bool:
    """Check if the tenant has an install token minted."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT settings FROM tenants WHERE id = $1", tenant_id)
    if not row:
        return False
    settings = safe_json_loads(row["settings"])
    return bool(settings.get(_SETTINGS_KEY))


async def set_install_token_hash(
    pool: asyncpg.Pool,
    tenant_id: UUID,
    token_hash: str | None,
) -> None:
    """Write (or clear) the install token hash on the tenant's settings JSONB.

    Uses ``jsonb_set`` for mint, ``-`` operator for revoke, so concurrent
    updates to other settings keys aren't clobbered.
    """
    async with pool.acquire() as conn:
        if token_hash is None:
            await conn.execute(
                "UPDATE tenants SET settings = settings - $2, updated_at = NOW() WHERE id = $1",
                tenant_id,
                _SETTINGS_KEY,
            )
        else:
            # asyncpg sends text[] as a Python list — jsonb_set takes a
            # text[] path (e.g. ['worker_install_token_hash']).
            await conn.execute(
                "UPDATE tenants SET settings = jsonb_set("
                "  COALESCE(settings, '{}'::jsonb), $2::text[], to_jsonb($3::text), true"
                "), updated_at = NOW() WHERE id = $1",
                tenant_id,
                [_SETTINGS_KEY],
                token_hash,
            )


async def resolve_install_token_tenant(pool: asyncpg.Pool, token: str) -> UUID | None:
    """Find the tenant that minted this install token, or None."""
    token_hash = hash_install_token(token)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM tenants WHERE settings->>$1 = $2 AND is_active = TRUE",
            _SETTINGS_KEY,
            token_hash,
        )
    return row["id"] if row else None
