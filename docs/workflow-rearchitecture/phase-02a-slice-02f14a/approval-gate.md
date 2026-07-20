# Slice 2F-14A Approval Gate

> **SUPERSEDED (Slice 2F-14B):** the coverage figure (158/210) and the framing of
> `create_job`/`convert_to_repair`/`spawn_repair`/quote-route gaps as distinct-capability/product
> questions were not fully accurate — `spawn_repair` had a live cross-tenant IDOR and missing
> duplicate guard, and `create_quote`/`create_job_quote`/`send_job_quote`/`respond_to_quote` had
> live ownership/impersonation defects, all fixed in Slice 2F-14B. See
> `docs/workflow-rearchitecture/phase-02a-slice-02f14b/documentation-corrections.md` and
> `docs/workflow-rearchitecture/phase-02a-slice-02f14b/approval-gate.md` for the current status.
> Content below retained for historical record.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

- **SECURITY_CLOSED**: All 6 staff-router mutations remain protected (re-verified, unchanged).
  Every same-Job alternate mutation on `field_ops.router` is classified
  (exact-runtime-route-reconciliation.csv, deferred-field-ops-route-classification.csv). The
  cross-tenant IDOR on `void_job` is fixed. Financial-looking live mutations
  (`close_job`/`generate_invoice`/`record_payment`/`deduct_commission`/`financial_close`) now
  have explicit, access-scope-aware authorization. Zero unverified mounted same-Job routes remain
  among the same-record-same-capability set — the 11 remaining unclassified-as-protected routes
  are all confirmed distinct capabilities (creation/quotes) with either an existing adequate
  service-level ownership check or an explicitly disclosed, non-bypass gap
  (product-decisions-required.md).
- **DOMAIN_INTEGRITY_CLOSED**: The finalized-checklist fix from 2F-14 remains intact (re-verified
  by full regression). Every same-Job completion/finalization route is reconciled
  (alternate-completion-finalization-audit.md) — no checklist-gate bypass found. Legacy checklist
  behavior is explicit (legacy-job-checklist-disposition.md). Invalid actions create no partial
  lifecycle side effects (verified: rejected `void_job`/checklist-item mutations leave `job.status`
  and `item.is_completed` unchanged in tests).
- **PRIVACY_CLOSED**: Unassigned technicians cannot read or mutate unrelated notes/media
  (verified). Customer-visible note content excludes provider-internal data (`is_internal`
  filtering, verified). Foreign Job/media/note IDs do not leak content (404, verified). No public
  route exposes Job notes or media (both require `_assert_can_access_job`). The one remaining gap
  — `JobMedia` has no internal/customer-visible column to filter on — is disclosed as a genuine
  schema limitation, not silently assumed closed, and does not constitute an access-control
  bypass (job-level ownership is still enforced).
- **GLOBAL_COVERAGE_CLOSED**: One canonical numerator (158) and denominator (210), fully
  reconciled from the 3 specific row-level defects found (2 duplicates, 1 false positive) plus 1
  categorization omission (`FULLY_PROTECTED`). The CSV recounts identically via an automated test
  that reads the file directly at test time. Runtime inventory (fresh tool runs against both
  field_ops routers) agrees with the documented per-route guard statuses.
- **PRODUCT_POLICY BLOCKED** for: `JobMedia` internal/customer-visible schema decision;
  `respond_to_quote`'s non-customer `customer_id` design ambiguity; legacy checklist deprecation
  timing; access-scope upgrade scope for creation-type routes; router-level defense-in-depth for
  quote routes. None of these are security gaps — all are genuine product/architecture calls.

## Scope discipline confirmed

No second router module was begun. `checklist_router`, `quote_checklist`, `PartsRequest`,
Booking/ServiceBooking were not modified. No role or alias was added. No new permission was
added — only two existing permission constants (`TENANT_UPDATE`, `FIELD_OPS_JOBS_CLOSE`) were
re-wrapped with the existing `require_tenant_mutation_permission` helper. No cross-pipeline
adapter was introduced. `readonly@demo-ac-services.local` untouched. Migration 144 unapplied. No
visual redesign occurred.

## Regression

192/192 in the slice-specific suite; 1226 passed in the broad partition sweep; 11 pre-existing
live-environment exclusions honestly separated out (regression-report.md).

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-14A approval gate. No
further router module is started.
