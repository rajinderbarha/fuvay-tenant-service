# Frontend Exposure Audit — The 8 Unassigned-Permission Endpoints

Workstream 5. Scope: `suspend`, `reinstate`, `terminate/begin`,
`terminate/confirm`, `plan/upgrade`, `plan/downgrade`, `trial/convert`,
`data/delete-request`.

## Method
Grepped every frontend application (`frontend/tenant-portal`,
`frontend/super-admin`, `frontend/customer-app`, `mobile/customer-app`) and
their API client files for the literal path fragments
(`/suspend`, `/reinstate`, `/terminate/begin`, `/terminate/confirm`,
`/plan/upgrade`, `/plan/downgrade`, `/trial/convert`, `/data/delete-request`)
against `${id}`/`${tenantId}` interpolation patterns matching
`/v1/tenants/{tenant_id}/...`.

## Findings, per endpoint

| Endpoint | Caller exists | Page | Button/action | Role visibility | Confirmation behavior |
|---|---|---|---|---|---|
| `/suspend` | YES — `frontend/super-admin/lib/api.ts:445` (`suspend`) | `admin/tenants/[id]/page.tsx`, `admin/customers/page.tsx`, `admin/customers/[id]/page.tsx` | Suspend action (super-admin app only) | super_admin only (separate frontend app) | `reason` string passed to the API call; no explicit modal confirmation code inspected this slice (out of scope: no frontend redesign) |
| `/reinstate` | YES — `api.ts:447` (`reinstate`) | same pages as above | Reinstate action | super_admin only | `reason` string passed |
| `/terminate/begin` | YES — `api.ts:449` (`beginTerminate`) | `admin/tenants/[id]/page.tsx` | Begin-termination action | super_admin only | `reason` string passed |
| `/terminate/confirm` | YES — `api.ts:451` (`confirmTerminate`) | `admin/tenants/[id]/page.tsx` | Confirm-termination action | super_admin only | no body/reason required by the client call |
| `/plan/upgrade` | YES — `api.ts:455` (`upgradePlan`) | `admin/tenants/[id]/page.tsx`, `admin/tenants/page.tsx` | Upgrade-plan action | super_admin only | `target_plan` + `reason` passed |
| `/plan/downgrade` | YES — `api.ts:457` (`downgradePlan`) | same pages | Downgrade-plan action | super_admin only | `target_plan` + `reason` passed |
| `/trial/convert` | YES — `api.ts:459` (`convertTrial`) | same pages | Convert-trial action | super_admin only | `plan_type` passed, no reason field |
| `/data/delete-request` | YES — `api.ts:505` | `admin/tenants/[id]/page.tsx` (data/privacy tooling) | Data-deletion-request action | super_admin only | `reason` string passed |

## Tenant-portal exposure
**Zero.** Grepped `frontend/tenant-portal/lib/api.ts` and every `.tsx` file
under `frontend/tenant-portal/app` for all 8 path fragments — no match
(confirmed via `grep -n "tenants/\${.*}/suspend\|.../reinstate\|.../terminate\|.../plan/\|.../trial/convert\|.../data/delete-request" frontend/tenant-portal/lib/api.ts`,
zero results). The only unrelated string matches in that file are the
`status: "suspended"` type-union member and a `suspended_at` field name — not
a caller of any of these endpoints.

## Customer-app / mobile exposure
Not applicable — these apps have no tenant-administration surface at all;
not separately audited beyond confirming they contain no `/v1/tenants/`
tenant-lifecycle calls (out of scope for this slice's mutation surface,
which is entirely tenant/admin-facing).

## Conclusion
Every one of the 8 endpoints has exactly one real caller today: the
super-admin frontend application, used by platform operations staff. No
tenant-portal (tenant_owner-facing) UI exposes any of them. **This is the
correct state and requires no change**: no replacement UI was added, no page
was redesigned, and the existing super-admin access was preserved
unmodified.

## Regression tests added
`tests/test_phase2f1_tenant_engine_mutation_enforcement.py::TestNoTenantPortalExposureForPlatformOnlyActions`:
- `test_tenant_portal_api_client_has_no_caller_for_platform_only_actions` —
  fails loudly if a future change adds a tenant-portal caller for any of the
  8 path fragments without an accompanying, explicit policy decision.
- `test_super_admin_api_client_still_has_all_eight_callers` — guards against
  silently losing the legitimate platform-admin access path.
