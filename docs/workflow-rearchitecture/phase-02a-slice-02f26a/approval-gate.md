# Slice 2F-26A Approval Gate

## Final status

**GLOBAL_COVERAGE_RECONCILIATION_BLOCKED**

Unchanged from the corrected status applied to Slice 2F-26 — and now with a
**named, reproducible reason** rather than an open population count.

## Coverage

`CURRENT_CANONICAL_COVERAGE`: **214 protected of 257**, 43 unprotected, 11
modules. **Unchanged.** Canonical CSV hash identical to the frozen slice-start
value (`45244cd9540456db`): no row added, none removed, none reclassified.

## Quality gates — honest assessment

| # | Gate | Status |
|---|---|---|
| 1 | All 123 mixed-persona routes adjudicated | **NOT MET** — evidence recorded for all 123; verdicts failed hand-verification and were not applied |
| 3 | All 7 held candidates resolved | evidence recorded; not applied (same tooling) |
| 4 | All 55 disagreements have final dispositions | recorded; not applied |
| 5 | 31 mutating GETs revalidated | **MET** — each has a final class |
| 6 | 145 read-only non-GET revalidated | **MET** — and 11 hidden side effects found |
| 7 | Hidden side effects promoted into the inventory | **NOT MET** — found, not yet promoted |
| 9 | Persona totals equal the genuine-mutation total | **NOT MET** |
| 21 | Verifier fails on incomplete-condition fixtures | **NOT BUILT** this slice |
| 23 | Baseline inputs frozen during runs | **MET** — hashes captured before any write; canonical untouched |
| 27–35 | Prior closures, roles, migrations, canaries, no frontend work | **MET** |

A slice that does not meet gates 1, 3, 4, 7, 9 and 21 cannot be reported as
reconciled. It is reported blocked.

## The two root causes

**1. "References `tenant_id`" ≠ "scopes to the caller's tenant."**
`POST /v1/tenants/{tenant_id}/suspend` (`Depends(require_super_admin)`) was
classified `TENANT_PROVIDER_MUTATION` because its service references
`tenant_id`. It is platform-admin. For routes acting *upon* a tenant named in
the path, the inference is inverted.

**2. Custom per-router guard aliases defeat static role resolution.**
`_provider_guard = require_owner_or_office_staff_mutation` is a local alias,
absent from the static dependency map, so role resolution silently degraded.
`POST /v1/provider/notifications/mark-all-read` was classified
`PLATFORM_INTERNAL_MUTATION` — a verdict that would have **removed a genuine
provider row belonging to the platform-notifications closure approved in the
2F-18 series**.

Both were found by hand-verifying the tool's output, not by the tool.

## Why nothing was applied

The verdicts would have added ~76 routes (including verified platform-admin
routes) and removed ~30 (including a verified provider route from a closed
module). Either direction corrupts the canonical record. Three iterations, three
hand-verification failures — a fourth unverified iteration was not a
responsible basis for editing the canonical inventory.

## Genuine finding carried forward

**11 of the 145 routes excluded as read-only POST/PUT/PATCH show side-effect
evidence.** If confirmed, they are mutations never persona-classified at all —
the same shape as the generic-prefix blind spot, along a different axis
(method-declared-read-only). Recorded in `read-only-nonget-revalidation.csv`.

## Required files not produced

This slice does not produce the full 33-file set. Files describing a completed
reconciliation — `complete-mutation-persona-partition.csv`,
`final-mutation-persona-arithmetic.md`, `canonical-coverage-arithmetic.csv`,
`authoritative-unprotected-module-queue.csv`,
`application-wide-verifier-hardening.md`, `verifier-negative-fixture-report.md`
and the associated reports — would describe work that did not complete.
Producing them would misrepresent the state. The five per-route evidence
artifacts that *are* real are written and listed in `implementation-summary.md`.

## Preserved

Zero application files modified. Zero authorization behaviour changed. Canonical
CSV byte-identical. All prior closures intact — field_ops, Booking,
quote-checklist, invoice-lineage, platform-notifications, compliance, Package
Commerce, customer_reviews, legacy review engine, legacy `POST /v1/reviews`
410. Canonical roles only; no role, permission or migration added; no pipeline
merged; `PartsRequest` ServiceJob-only; `readonly@` untouched; Migration 144
unapplied; Slice-2D canaries untouched.

## Stop condition

Stops at the Slice 2F-26A approval gate. No module selected, no authorization
implemented, no canonical change made. The next slice needs guard-alias
enumeration and tenant-predicate dataflow analysis before adjudication can be
trusted — specified in `implementation-summary.md`.
