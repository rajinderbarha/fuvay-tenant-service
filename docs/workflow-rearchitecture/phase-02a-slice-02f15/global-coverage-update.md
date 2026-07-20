# Global Coverage Update — Slice 2F-15

## Starting canonical baseline

169 protected of 210 tenant-facing mutation routes (Slice 2F-14G).

## Booking-engine inventory (freshly added — previously 0 rows tracked)

`app.engines.booking.router` has **11** mounted mutation-method (POST/PUT/PATCH/DELETE) routes,
confirmed via fresh runtime tool run. None were previously present in the canonical CSV.

## Routes newly protected this slice

- `create_booking` — fixed (customer validation + relationship requirement + guard upgrade to
  `require_tenant_mutation_permission`).
- `confirm_booking` — guard upgraded to `require_tenant_mutation_permission`.
- `reject_booking` — guard upgraded to `require_tenant_mutation_permission`.
- `convert_to_job` — guard upgraded to `require_tenant_mutation_permission`.

= **4 newly protected routes.**

## Already-protected routes

- `void_booking` — already `PLATFORM_ADMIN_ONLY` (`require_super_admin`), unchanged.

## Remaining unprotected Booking routes (out of scope this slice)

- `booking_preflight` — read-only, not a mutation of persistent state in the authorization sense
  (no `Booking` row created/changed).
- `cancel_booking`, `accept_reschedule`, `reject_reschedule`, `request_reschedule` — distinct
  capabilities (cancellation/reschedule), not part of the create/confirm/convert chain this
  slice's mission scopes to.
- `add_note` — same class of gap already fixed for `field_ops.router`'s own `add_note`
  (Slices 2F-14A/C); flagged as a follow-up candidate, not fixed here.

= **6 rows remain unprotected/out-of-scope**, all explicitly classified (not left
`UNVERIFIED`/unclassified).

## Excluded from the tenant-mutation denominator entirely

None — `booking_preflight` and the customer self-service aspects of `create_booking` are counted
within the SAME 11 rows as the tenant-facing capability (per the CSV's existing convention for
dual-persona routes, matching how `field_ops.router`'s `create_job` was counted in prior slices)
— not double-counted, and not separately tallied as a customer-only denominator.

## Canonical result

**213 (Slice 2F-14G total) reconciled + 11 new booking rows = 221 total tenant-facing mutation
routes.**

**169 (prior protected) + 4 (booking fixes) + 1 (void_booking, already protected, newly counted) =
174 protected of 221.**

Verified via direct Python recount against the single master CSV:
```
total 221
protected 174
duplicate keys: []
false positives: 0
```

## Both CSVs recount identically

`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount`
(updated this slice) asserts `total == 221`, `protected == 174` directly against the CSV file.
No separate "headline convention" is used — this is the single, canonical figure.
