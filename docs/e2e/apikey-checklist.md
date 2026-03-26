# API Key Feature - E2E Checklist

## Key Generation & Storage
- [x] API key format: `bsg_live_` + 32 random bytes hex (64 chars)
- [x] Key stored as SHA-256 hash (not plaintext)
- [x] Full key returned only on creation (once)
- [x] Key prefix (first 12 chars) stored for display

## CRUD Endpoints
- [x] POST `/api/v1/tenants/{tenant_id}/api-keys` creates key, returns full key
- [x] GET `/api/v1/tenants/{tenant_id}/api-keys` lists keys (no secrets)
- [x] DELETE `/api/v1/tenants/{tenant_id}/api-keys/{key_id}` revokes key

## Dual Auth Middleware
- [x] `Authorization: Bearer bsg_live_xxx` → API key auth → resolves tenant
- [x] `Authorization: Bearer eyJxxx` → JWT auth (existing path)
- [x] Missing/invalid header → 401
- [x] Expired API key → 401
- [x] Revoked (is_active=false) API key → 401

## Chat Integration
- [x] `/api/v1/chat/completions` works with API key auth (same `get_auth_context` dep)
- [x] Correct tenant_id resolved from API key

## Access Control
- [x] Tenant member can create/list/revoke own keys
- [x] Cannot access other tenant's keys (403)
- [x] Admin can access any tenant's keys

## Security
- [x] Key hash is not reversible (SHA-256)
- [x] Full key never logged (only prefix logged)
- [x] last_used_at updated on auth
