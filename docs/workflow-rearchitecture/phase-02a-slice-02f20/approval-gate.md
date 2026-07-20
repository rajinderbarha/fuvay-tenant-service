# Slice 2F-20 Approval Gate

## Final status

**SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED**

## Rationale

### Security dimension: CLOSED
All 6 mounted mutation routes in `app.engines.compliance.provider_router`
(`create_my_request`, `cancel_my_request`, `withdraw_consent`,
`generate_export`, `customer_tenant_response`, `staff_tenant_response`),
plus the GET route `download_export`, now resolve
`require_tenant_owner_mutation` — a canonical, pre-existing,
access-scope-aware dependency admitting only `tenant_owner`/`super_admin`
(no new role, alias, or permission). Specifically:
- Tenant authority is never passed as `None` — `withdraw_consent`'s
  hardcoded `tenant_id=None` defect is fixed for the tenant-scoped
  caller (`consent-withdrawal-integrity.md`).
- `create_my_request`'s tenant-ownership stamping is now atomic (single
  constructor call, no separate post-insert UPDATE window)
  (`compliance-metadata-tenant-integrity.md`).
- No route accepts a client-supplied tenant_id or subject_id that bypasses
  server-derived authority — confirmed structurally
  (`compliance-tenant-authority-contract.md`, `data-subject-identity-authority.md`).
- No weaker same-record alternate route exists
  (`compliance-alternate-route-audit.md`) — `customer_router.py`'s
  subject-scoped routes and `admin_router.py`'s platform-wide routes are
  both independently and correctly scoped for their own personas.
- Cross-tenant/cross-subject IDOR was checked via a dedicated test matrix
  (`compliance-idor-subject-test-matrix.csv`, `direct-authorization-test-matrix.csv`)
  — none found among the 6 selected routes.
- Runtime verification exits 0 for all 7 routes
  (`runtime-verification-report.md`).

### Domain-integrity dimension: BLOCKED
Per this slice's own explicit prohibition — "Do not claim domain-integrity
closure while the export worker is unlocated, unscoped, or able to
generate duplicate/conflicting exports" — closure is NOT claimed, because:
- No export-generation worker exists anywhere in the codebase; every
  export a tenant generates is permanently stuck in `"processing"`
  (`compliance-export-worker-discovery.md`). This is conclusively
  documented as absent, not fabricated and not left ambiguously
  "unlocated."
- `generate_export` has no deduplication/idempotency check; repeated
  calls (or a race with the admin `process_request` path) can and do
  create multiple independent, permanently-stuck export rows for one
  request (`compliance-export-retry-concurrency.md`).

These are pre-existing defects, not introduced or worsened by this
slice's changes, and are explicitly out of proportion to fix within an
authorization-focused, migration-free slice (see
`product-decisions-required.md`).

## Coverage
**206 protected of 226** tenant-facing mutation routes (was 200/226).
+6, all from this slice's module. Denominator unchanged. Both canonical
CSVs updated and both recount tests pass
(`canonical-coverage-update.md`).

## Preserved (re-confirmed unchanged)
- `field_ops.router`/`staff_router` closures intact.
- Booking authorization and provenance closure intact.
- Quote-checklist authorization and privacy closure intact.
- The six-slice `platform_notifications`/chat-media closure (2F-18
  through 2F-18E) intact and unmodified.
- `PartsRequest` remains ServiceJob-only, unmodified.
- `Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` separation
  intact.
- `readonly@demo-ac-services.local` untouched.
- Migration 144 unapplied; no migration added or applied this slice.
- `customer_router.py`'s and `admin_router.py`'s compliance mutations
  unmodified and unaffected.
- All previously-approved tests pass; full regression detail in
  `regression-report.md`.

## Scope discipline confirmed
No new role, alias, or permission was added — only the canonical,
pre-existing `require_tenant_owner_mutation` dependency (already defined
in `app/core/permissions.py`, previously unused) was wired in. No
migration was added or applied; `ComplianceRequest`/`ComplianceExport`
schema was not redesigned — the missing `tenant_id` column gap is
explicitly left open per instruction, addressed instead via server-owned,
atomically-written `metadata_json` fields with fail-closed WHERE-clause
comparisons. No `Booking`/`ServiceBooking` or `field_ops.Job`/`ServiceJob`
merge occurred. `PartsRequest`, `quote_checklist`, `platform_notifications`,
and chat-media authorization were not touched. No frontend/visual
redesign occurred. No `My Work`/Next-Action aggregation or Booking
Exception Resolution work was done.

## Stop condition
Per this slice's closing instruction, this response stops at the Slice
2F-20 approval gate. No other module has been begun or selected. The
2F-19 non-selected module queue (9 modules, 20 routes) is unchanged and
carried forward as-is (`remaining-module-queue-update.csv`) as the basis
for whichever future slice selects the next module.

## Forward annotation (added by Slice 2F-21)
Slice 2F-21 reconciled this slice's carried-forward 9-module/20-route
queue and selected the next authorization module. This slice's closure is
CONFIRMED to stand, unmodified: all 20 remaining routes were runtime
re-verified against `app.engines.compliance.provider_router`'s changes and
found to have ZERO indirect impact (2F-20 only ever touched files under
`app/engines/compliance/`; none of the 20 remaining routes' modules import
or reference anything under that path —
`compliance-indirect-change-audit.md`). The 206/226 coverage baseline this
slice established is UNCHANGED — 2F-21 found zero row-level evidence for
any numerator or denominator correction
(`canonical-coverage-reconciliation.md`). 2F-21 selected
`app.engines.package_commerce.tenant_router` (its sole mutation route,
`POST /v1/tenant/packages/{package_id}/purchase`) as the next module for
Slice 2F-22, re-deriving the queue CSV's prior rank-1 candidacy from
direct source code (not merely repeating the prior ranking) and
additionally surfacing a `CLIENT_AMOUNT_TRUSTED`-class gap on that route's
`mark_paid` field not previously documented. Final status for 2F-21 is
`NEXT_MODULE_SELECTED_COVERAGE_UNCHANGED` — a discovery/selection slice,
not an implementation slice; the domain-integrity gap this slice's own
closure explicitly left BLOCKED (export-generation worker) was NOT
reopened by 2F-21, per 2F-21's own scope prohibition. See
`../phase-02a-slice-02f21/approval-gate.md` for full detail.
