from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from bsgateway.api.deps import (
    GatewayAuthContext,
    get_pool,
    require_tenant_access,
)
from bsgateway.apikey.models import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyInfoResponse,
)
from bsgateway.apikey.service import ApiKeyService

router = APIRouter(prefix="/tenants/{tenant_id}/api-keys", tags=["api-keys"])


def _get_apikey_service(request: Request) -> ApiKeyService:
    pool = get_pool(request)
    return ApiKeyService(pool)


@router.post(
    "",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
)
async def create_api_key(
    tenant_id: UUID,
    body: ApiKeyCreate,
    request: Request,
    _auth: GatewayAuthContext = Depends(require_tenant_access),
) -> ApiKeyCreatedResponse:
    svc = _get_apikey_service(request)
    result = await svc.create_key(
        tenant_id,
        body.name,
        scopes=body.scopes,
        expires_in_days=body.expires_in_days,
    )
    return ApiKeyCreatedResponse(
        id=result.id,
        tenant_id=result.tenant_id,
        name=result.name,
        key_prefix=result.key_prefix,
        raw_key=result.raw_key,
        scopes=result.scopes,
        created_at=result.created_at,
    )


@router.get(
    "",
    response_model=list[ApiKeyInfoResponse],
    summary="List API keys",
)
async def list_api_keys(
    tenant_id: UUID,
    request: Request,
    _auth: GatewayAuthContext = Depends(require_tenant_access),
) -> list[ApiKeyInfoResponse]:
    svc = _get_apikey_service(request)
    keys = await svc.list_keys(tenant_id)
    return [
        ApiKeyInfoResponse(
            id=k.id,
            tenant_id=k.tenant_id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            is_active=k.is_active,
            expires_at=k.expires_at,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
)
async def revoke_api_key(
    tenant_id: UUID,
    key_id: UUID,
    request: Request,
    _auth: GatewayAuthContext = Depends(require_tenant_access),
) -> None:
    svc = _get_apikey_service(request)
    await svc.revoke_key(key_id, tenant_id)
