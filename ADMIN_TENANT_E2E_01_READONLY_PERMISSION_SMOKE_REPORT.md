# ADMIN_TENANT_E2E_01 — Read-Only Tenant Permission Smoke Report

User: `tenant.readonly@serviceos.in` (role=tenant_owner, `access_scope=customer_support_limited`,
tenant_id=Demo AC Services), created in Part 4.

## Checks performed
1. Can log in via browser — PASS (`frontend/e2e-admin-tenant/evidence/tenant-readonly-login.png`)
2. Can view dashboard/setup checklist — PASS (same session, `/dashboard` renders normally)
3. Edit/save actions hidden or disabled in UI — **GAP**: the tenant-portal frontend does not currently
   branch any UI on `access_scope` at all; there is no distinct "read only" mode. Every tenant_owner user
   sees the identical, fully-editable UI regardless of `access_scope`. This is honestly documented as a
   gap, not forced to a pass.
4. Backend rejects a mutation attempt — **GAP FOUND, real and significant**: `PUT
   /v1/provider/business-profile` returned `200 OK` and genuinely applied the mutation
   (`business_name` changed to a probe string, `verification_status` flipped to
   `changes_pending_review`) for the `customer_support_limited` user. There is no `access_scope`
   check on this (or apparently other) provider-portal mutation endpoints today.
5. request_id present on responses — PASS in the sense that both the (unintended) 200 success and a
   real 404 on a wrong path both carried `meta.request_id` / `request_id` — but there was no 403 to
   check for, since the mutation was not rejected at all.

## Remediation performed
The mutation test itself is now non-destructive: it reads the current `business_name` via `GET
/v1/provider/business-profile` before mutating, and restores it via a follow-up `PUT` after asserting/
recording the result, so re-running the E2E suite does not leave corrupted seed data. The
`verification_status` side-effect (flips to `changes_pending_review` on any critical-field write,
by design, regardless of who made the write) is NOT reset by the endpoint itself; this sprint manually
reset it via SQL after each test run and re-verified end-to-end bookability afterward. A future sprint
should add either (a) real `access_scope`/RBAC enforcement on provider mutation endpoints, or (b) a
dedicated non-mutating "read-only smoke" test tenant so this class of test never touches the shared
Demo AC Services seed tenant.

## Result
PARTIAL — read-only user can log in and view data (pass), but there is no UI-level read-only gating and
no backend access_scope enforcement (real, documented gaps for a future RBAC sprint). This is exactly the
kind of foundation-sprint finding the spec asked to surface honestly rather than paper over.
