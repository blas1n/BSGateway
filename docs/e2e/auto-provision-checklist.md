# Tenant Auto-Provision - E2E Checklist

## Auto-Provision
- [x] JWT with new tenant_id → tenant auto-created in DB
- [x] Tenant name/slug derived from tenant_id (short prefix)
- [x] Subsequent requests use existing tenant (no re-create)

## Still Blocked
- [x] Explicitly deactivated tenant (is_active=false) → 403
- [x] API key auth does NOT auto-provision (key must map to existing tenant)

## No Manual Create Needed
- [ ] Dashboard loads on first login without manual tenant creation
