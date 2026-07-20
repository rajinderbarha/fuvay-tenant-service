# Compliance Service-Layer Bypass Report

## `ComplianceEnterpriseService.create_request` — callers
- `provider_router.create_my_request` — constructs `subject_type`/
  `subject_id`/`metadata_json` server-side from the authenticated
  principal. STRONGEST input discipline of the three callers.
- `customer_router.create_my_request` — same pattern, server-derived from
  the customer principal.
- `admin_router.create_request` (line ~90) — passes the RAW client body
  directly with no server-side derivation at all. WEAKEST input
  discipline — but gated by `require_super_admin`, the platform's
  strongest role, so this is an accepted trust boundary (an admin
  operator is trusted to supply correct `subject_type`/`subject_id`
  values), not a bypass of tenant-side authorization.
- This slice's fix (`metadata_json` now atomically persisted) applies
  IDENTICALLY to all three callers — `create_request` itself was the
  shared fix point, so no caller-specific patching was needed.

## `ComplianceEnterpriseService.revoke_consent` — callers
- `provider_router.withdraw_consent` — NOW passes real `tenant_id` (this
  slice).
- `customer_router.withdraw_my_consent` — correctly continues to pass no
  `tenant_id` (customers have none).
- `admin_router.revoke_consent` — correctly continues to pass no
  `tenant_id` (platform-wide action, no single tenant to attribute).
- Service method fails closed for missing tenant scope: N/A here —
  `tenant_id=None` is a VALID state for 2 of 3 callers by design; the
  service method itself has no way to distinguish "legitimately no
  tenant" from "tenant lost due to a bug" — this slice's fix works by
  ensuring the ONE caller that HAS a tenant always supplies it, not by
  making the service reject `None` outright (which would break the other
  two legitimate callers).

## Strongest and weakest caller
Strongest: `admin_router` (role: `super_admin`, but weakest input
validation — an accepted trade-off for a trusted-operator surface).
Weakest (pre-2F-20): `provider_router` (role: `tenant_owner` only, but
had the `tenant_id=None` defect and the non-atomic metadata write) — now
fixed, no longer the weakest link.

## `tenant_id=None` must never become a global/unscoped query mode
Confirmed: `revoke_consent`'s `tenant_id=None` only ever affects WHAT IS
WRITTEN to a NEW `ConsentRecord` row — it never becomes a query filter
that could return OTHER tenants' data. No read path in this module
queries `ConsentRecord` with `tenant_id IS NULL` as a wildcard/global
filter — confirmed by grep across `service.py`/`enterprise_service.py`.
