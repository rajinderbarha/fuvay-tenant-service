# Frontend Exposure Audit — Slice 2F-2

## Method
Grepped `frontend/tenant-portal/lib/api.ts` for every one of the 24
provider-portal mutation path fragments; checked `frontend/super-admin` and
`mobile/customer-app` for any overlapping calls.

## Findings
All 24 endpoints have a real caller in `frontend/tenant-portal/lib/api.ts`
(lines ~2460-2784), used from the tenant-owner-facing tenant-portal app:
team-members roster page, availability/business-hours settings, offerings
selection settings, booking-window settings, provider status/onboarding
refresh actions. No caller was found in `frontend/super-admin` or any
customer/mobile app for any of these 24 paths — confirming this router's
entire mutation surface is tenant-owner self-service, never a platform-admin
or customer capability, consistent with all 24 endpoints' final
`TENANT_OWNER_SELF_SERVICE` / `FALSE_POSITIVE` classifications.

## Role visibility vs. backend policy
No staff or technician role can reach any of these 24 endpoints
server-side (`require_tenant_owner`/`require_tenant_owner_mutation`
excludes both). The tenant-portal frontend's team-management and
availability/offerings settings pages are rendered inside owner-scoped
layout sections (not separately re-audited pixel-by-pixel this slice, since
no frontend code was changed — verifying the *backend* denies staff/
technician access, which it does, is the security-relevant guarantee; a
staff/technician user attempting these actions via direct API call, not
just via a hidden button, is correctly rejected).

## No exposure change required
Because every one of the 24 endpoints was already tenant-owner-only in the
frontend (no staff/technician-facing button ever called these paths), no
frontend change was needed and none was made — consistent with "do not add
new frontend functionality" and "make only the smallest access-alignment
change if current UI exposure is unsafe" (it was not unsafe; only the
backend access-scope gap needed closing).

## Regression test
`tests/test_phase2f2_provider_portal_mutation_enforcement.py::TestUnauthorizedRolesRejected`
directly proves staff/technician/customer roles are rejected server-side,
independent of any frontend visibility state.
