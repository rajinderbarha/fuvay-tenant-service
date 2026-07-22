# Application-Wide Claim Boundary

## What is certified

- The **313 canonical tenant/provider mutations** identified across
  Slices 2F-35/36/37 are protected, with 0 unprotected, independently
  reconfirmed by live route/guard introspection in this slice
  (`verify_2f37.py` 21/21 PASS, re-derived not copied).
- Exactly the 10 canonical roles are executable; no alias grants access
  through any path this slice traced.
- Full `tests/test_phase2f*.py` regression (2445 tests) passes
  deterministically.

## What is explicitly NOT certified by this slice

- **Application-wide mutation authorization.** Of ~1,186 total
  auto-detected mutation routes, only the 313 canonical ones received the
  full manual audit this program's methodology requires. 261 routes
  remain classifier-`UNVERIFIED`; 89 more were only spot-checked (12 of
  89), not individually certified. See `mutation-disposition-census.md`.
- **Persisted role-data integrity beyond the 2 known accounts.** No live
  database exists to scan for other invalid role values.
- **Migration 144 runtime safety.** No PostgreSQL environment was
  available to apply/rollback/reapply it.
- **Demo-account remediation.** Both `manager@`/`readonly@demo-ac-services.local`
  remain `MANUAL_ROLE_CONFIRMATION_REQUIRED`.
- **N01 domain integrity** — remains `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`.
- **Payments financial integrity** — client-supplied amounts and absent
  authoritative ledger remain unresolved.
- **Read-path tenant privacy** for pricing GET-by-zone/rule-ID and
  item/location ownership.
- **Product-policy completeness** — Booking Exception Resolution and
  customer cancellation/rescheduling remain unresolved.
- **Full-repository regression** — see `full-backend-regression-report.md`
  for whether this passed.

No claim beyond these bounds should be inferred from this slice's work.
