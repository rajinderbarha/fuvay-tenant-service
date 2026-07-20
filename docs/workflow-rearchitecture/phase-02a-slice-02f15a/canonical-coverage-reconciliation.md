# Canonical Coverage Reconciliation

## Baseline (Slice 2F-15, provisional)
174/221 tenant-mutation rows protected, per `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`. This included all 11 `booking.router` rows (5 protected: `create_booking`, `confirm_booking`, `reject_booking`, `convert_to_job`, `void_booking`; 5 unprotected: `cancel_booking`, `accept_reschedule`, `reject_reschedule`, `request_reschedule`, `add_note`; 1 uncounted as a distinct category: `booking_preflight`, `PERMISSION_ONLY_NOT_SCOPE_AWARE`).

## Reclassification performed this slice
Per Workstream 17's explicit instruction not to preserve 221 "merely for continuity":

1. **`booking_preflight` removed from the mutation denominator entirely** — reclassified `FALSE_POSITIVE_NO_PERSISTENCE` (confirmed zero persistence). It was never a mutation; counting it in either numerator or denominator misrepresents coverage. **Denominator: 221 → 220.**
2. **5 previously-unprotected routes fixed and now verified protected**: `cancel_booking`, `accept_reschedule`, `reject_reschedule`, `request_reschedule`, `add_note`. **Numerator: 174 → 179.**
3. **Persona reclassification** (does not change the numerator/denominator, but corrects category labels): of the 10 remaining `booking.router` mutation rows, 9 are `DUAL_CUSTOMER_TENANT_MUTATION` or `TENANT_ONLY_MUTATION` (tenant-facing) and 1 (`void_booking`) is `PLATFORM_ADMIN_ONLY_MUTATION` (not tenant-facing, but already counted correctly as protected in both the old and new figures — its classification was already accurate, only its neighbors' were wrong).

## Result
**179/220 tenant-mutation-route protections verified (81.4%).**

`app.engines.booking.router` itself: 10/10 mutation rows fully accounted for — 9/9 tenant-facing mutations protected + 1/1 platform-admin-only mutation protected = **10/10 (100%)**, up from the provisional 5/11 (45%) reported at the 2F-15 gate.

`field_ops.router` (28/28) and `field_ops.staff_router` (6/6) are unchanged and re-confirmed, contributing 34 of the 179 protected rows, as before.

## What this reconciliation does NOT claim
This coverage figure describes ONLY the 220 rows already inventoried in the canonical CSV (accumulated slice-by-slice across this entire initiative). It is not a claim that every mutation route in the entire ServiceOS codebase has been inventoried — routers outside this initiative's slice history remain unaudited, as has been true at every prior gate.
