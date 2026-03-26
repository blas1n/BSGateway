from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- Request/Response schemas (Pydantic) ---


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable key name")
    scopes: list[str] = Field(default=["chat"], description="Permission scopes")
    expires_in_days: int | None = Field(
        None, ge=1, le=365, description="Days until key expires (None = no expiry)"
    )


class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    key_prefix: str
    raw_key: str = Field(description="Full API key — shown only once")
    scopes: list[str]
    created_at: datetime


class ApiKeyInfoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


# --- Internal dataclasses ---


@dataclass
class ApiKeyCreated:
    id: UUID
    tenant_id: UUID
    name: str
    key_prefix: str
    raw_key: str
    scopes: list[str]
    created_at: datetime


@dataclass
class ApiKeyInfo:
    id: UUID
    tenant_id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


@dataclass
class ValidatedKey:
    key_id: UUID
    tenant_id: UUID
    scopes: list[str]
