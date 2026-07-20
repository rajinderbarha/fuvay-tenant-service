# Known Limitations — Slice 2F-5A

1. **`finance_hub`'s internal tenant/object-ownership enforcement was not
   traced line-by-line** — this slice confirmed WHO can call each
   endpoint (permission-bundle analysis) but not the exact internal
   mechanism enforcing deposit/payout/claim record ownership. Flagged for
   the next slice.
2. **`UsageCreditService`'s full internals were not re-audited** — trusted
   as already-canonical per the FINAL-L5-05J historical fix, not
   independently re-verified for idempotency/precision/concurrency this
   slice.
3. **Commission calculation/deduction service internals were not traced**
   — both endpoints are `require_super_admin`-gated regardless, so the
   guard-level finding stands, but the service-layer correctness was not
   independently re-verified.
4. **The credit-wallet top-up idempotency gap (defaults to a random key if
   the caller doesn't supply one) was identified but not fixed** — fixing
   it would require understanding `UsageCreditService`'s full idempotency
   contract, out of this slice's narrow scope. See
   `product-decisions-required.md` item 4.
5. **Whether `finance_hub`'s payout/claims endpoints have real
   super-admin-app frontend callers was not definitively confirmed** — 53
   combined path-fragment matches were found in
   `frontend/super-admin/lib/api.ts` across BOTH modules, not
   individually attributed per-endpoint this slice.
6. **The relationship between `package_commerce`'s admin package CRUD and
   any read-side/catalog-browsing implementation was not traced** — only
   the write side was audited (per the mission's mutation-route scope).
7. **A full-repository test run was not completed** — 907 combined tests
   (293 targeted + 614 broader finance partition), 4 pre-existing skips, 0
   real failures, is the evidence base.
8. **`readonly@demo-ac-services.local` remains untouched; migration 144
   remains unapplied; the 6 previously security-closed modules were not
   modified** — all confirmed per the brief's explicit exclusions. No code
   was changed in either `package_commerce` or `finance_hub` this slice —
   this was purely an adjudication.
