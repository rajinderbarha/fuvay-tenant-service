# Slice 2F-14B Approval Gate

> **SUPERSEDED (Slice 2F-14C):** `SECURITY_CLOSED` was asserted below while `add_note`/
> `add_media` remained 2 of 28 mounted `field_ops.router` mutations outside the tool-verified
> protected set (26/28, not 28/28) — the real service-level ownership fix from Slice 2F-14A was
> never backed by a router-level persona/mutation-scope dependency, and no test proved a
> read-only-scoped tenant account was denied. `create_job` also accepted `service_type_id`/
> `parent_job_id`/`booking_id` with zero tenant-ownership validation. All fixed in Slice 2F-14C.
> See `docs/workflow-rearchitecture/phase-02a-slice-02f14c/documentation-corrections.md` and
> `docs/workflow-rearchitecture/phase-02a-slice-02f14c/approval-gate.md` for the current status.
> Content below retained for historical record.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

- **SECURITY_CLOSED**: Every genuine tenant creation/conversion mutation
  (`create_job`/`convert_to_repair`/`spawn_repair`) is now mutation-scope protected via
  `require_tenant_mutation_permission`. Every genuine customer decision route
  (`respond_to_quote`/`approve_job_quote`/`reject_job_quote`) requires `require_customer`, with
  `customer_id` always derived from the authenticated principal — no override possible. Tenant,
  customer, Job, source, and quote ownership are enforced at the service layer for every route in
  scope. `customer_id`/`tenant_id` cannot override authoritative identity (fixed this slice).
  Wrong personas are denied (customer denied from quote administration; non-customer denied from
  quote decisions). No weaker service or alternate caller remains among the 9 routes fixed this
  slice. Of `field_ops.router`'s 28 mounted mutations, 26 are now tool-verified protected; the
  remaining 2 (`add_note`/`add_media`) have a verified but tool-invisible service-level fix from
  Slice 2F-14A — disclosed, not claimed as tool-verified.
- **DOMAIN_INTEGRITY_CLOSED**: Creation/conversion duplicate behavior is explicit
  (`spawn_repair`'s missing duplicate guard fixed; `convert_to_repair`'s was already correct).
  Source-to-target state consistency preserved (tenant/customer always derived from source, never
  request). Quote state transitions are explicit and verified (`pending`/`draft`/`sent`/
  `approved`/`rejected`/`expired`). Customer decisions affect the correct quote
  (`quote.customer_id`/`quote.job_id` matching enforced). Invalid requests create no partial
  records (verified: all guards raise before any `db.add`). Quote decisions create no
  unauthorized financial effects (verified: no quote route calls `BillingService`).
- **PRIVACY_CLOSED**: Customer identity cannot be impersonated (fixed — `respond_to_quote` no
  longer accepts a client-supplied `customer_id`). Cross-customer and cross-tenant quote data
  remains isolated (404 on any mismatch, no distinguishing leak). Audit actors represent the real
  caller (fixed — `_write_history`'s recorded actor is now guaranteed accurate for quote
  responses). No foreign customer PII is leaked (verified via privacy-test-matrix.csv).
- **PRODUCT_POLICY BLOCKED** for: legacy vs. richer quote-surface consolidation;
  `create_job`'s FK-validation hardening; `JobMedia` internal/customer-visible schema (carried
  over); legacy checklist deprecation timing (carried over). None of these are security gaps.

## Scope discipline confirmed

No second router module was begun. `field_ops.staff_router`, `checklist_router`,
`quote_checklist`, `PartsRequest`, Booking/ServiceBooking were not modified. No role or alias was
added. No new permission was added — only existing permission constants
(`TENANT_UPDATE`, `FIELD_OPS_JOBS_ASSIGN`) were re-wrapped with the existing
`require_tenant_mutation_permission`/`require_staff_or_above_mutation`/`require_customer`
dependencies. No cross-pipeline adapter was introduced. `readonly@demo-ac-services.local`
untouched. Migration 144 unapplied. No visual redesign occurred.

## Coverage

**167 protected of 210** tenant-facing mutation routes (up from the approved 158/210 baseline).
field_ops subtotal: 38/40. Both figures recount identically from the single master CSV via an
automated test.

## Regression

85/85 in the slice-specific suite; 1264 passed in the broad partition sweep; 15 pre-existing
live-environment exclusions honestly separated out.

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-14B approval gate. No
further router module is started.
