# Canonical Coverage Reconciliation

## Starting approved baseline
190/226 (pre-2F-18) → 200/226 (2F-18/2F-18A, router-level guard fix).

## This slice's reconciliation of all 10 selected routes
See `final-selected-route-protection.csv` for the row-by-row table. All 10
routes are confirmed `FULLY_PROTECTED` under the mission's own definition
("Only routes satisfying every applicable policy may become
FULLY_PROTECTED"):

- **Persona/mutation-scope status**: unchanged, `require_owner_or_office_staff_mutation`/
  `require_staff_or_technician_only` — re-confirmed via live runtime
  introspection (identical output to 2F-18/2F-18A).
- **Thread/recipient/participant/assignment status**: unchanged from
  2F-18A (technician assignment/participant policy).
- **Attachment authorization status**: **advanced this slice** from
  "tenant-only" (2F-18A) to full reuse of `MediaAccessService` plus
  context/lifecycle/customer checks — the ONE route that accepts
  attachments (`provider_send_message`) is now genuinely
  `FULLY_PROTECTED` on this dimension, not merely "not obviously broken."
  `staff_send_message`'s attachment field is a pre-existing non-functional
  no-op (never forwarded) — classified `FALSE_POSITIVE`, not a gap,
  because there is no live attachment path to protect or fail to protect.
- **Privacy status**: unchanged from 2F-18A (thread errors) plus this
  slice's own attachment-error privacy equivalence (see
  `media-error-privacy-equivalence.md`).
- **Alternate-route status**: `customer_router.py` has no media field on
  `SendMessageIn` at all — confirmed no weaker alternate attachment path
  exists.

## Arithmetic — NOT automatically 200/226
Per the mission's explicit instruction not to auto-report 200/226, this
slice independently verified: **190 (baseline) + 10 (all ten selected
routes, individually confirmed fully protected on every dimension
including the previously-open attachment dimension) = 200.** The
denominator (226) is unchanged — no row-level persona evidence changed
this slice (no route was added, removed, or reclassified as
customer/platform/false-positive).

**Result: 200/226 — earned, not assumed**, because all ten routes'
previously-open attachment-authorization gap is now closed at the depth
this slice's investigation could achieve (tenant+customer+context+lifecycle+
principal-level `MediaAccessService` reuse), with the one residual gap
(cross-Job/cross-conversation lineage, unachievable with current schema)
honestly disclosed rather than silently ignored.

## Both canonical CSVs recount identically
Unchanged from 2F-18/2F-18A — no row was touched this slice.
`tenant-mutation-endpoint-inventory.csv` (226 rows, 200 protected) and
`mutation-enforcement-matrix.csv` remain exactly as 2F-18 left them.
`test_canonical_totals` and
`test_global_numerator_denominator_match_2f17_baseline` (both asserting
`total==226, protected==200`) pass unchanged, re-confirmed by this slice's
regression run.

## Remaining module count
Unchanged: 26 unprotected tenant/provider mutation routes across the 10
non-selected modules — this slice touched only `platform_notifications`.
