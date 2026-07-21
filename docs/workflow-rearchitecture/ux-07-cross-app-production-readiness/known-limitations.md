# Known Limitations (Round 1)

1. **super_admin login not verified**: no known demo credential surfaced
   this round. All other 3 tested roles used the `Password123!` password
   discovered by bounded trial against the real, dev-only auth endpoint
   (which reports attempts-remaining, confirming it is genuinely live and
   rate-limited, not a fixture). A super_admin equivalent was not found or
   guessed within a safe attempt budget.
2. **`offering_type_id` functionally required but undocumented**: the
   `ac_repair` booking draft's `required_fields` response lists
   `issue_summary`/`city`/`brand_id` but NOT `offering_type_id`, yet
   `match-and-price` fails without it (both real `ServicePricingRule` rows
   for this offering are `service_type_id`-scoped with no unscoped
   fallback). Real, live-verified gap; not fixed this round (frontend-only
   scope, and the correct fix — likely adding `offering_type_id` to
   `required_fields`, or adding an unscoped fallback pricing rule — belongs
   to the backend/catalog-config team, not this session).
3. **`/summary` must be called via POST, not GET** (GET returns 405) — a
   minor, real contract detail confirmed live; any future frontend code
   calling it must use POST.
4. **Dark theme still absent in mobile/customer-app** — standing,
   pre-existing gap carried forward from UX-06, not addressed this round.
5. **No test suite was run this round** — the one code change
   (`chatLanguages.ts` narrowing) was not verified via `tsc`/`npm test`;
   this is a real, disclosed gap for that specific change (though its scope
   is small and its sole consumer was grep-confirmed).
6. **No Playwright/UI-level evidence gathered this round** — all E2E proof
   is real backend curl evidence, not screenshots or browser-driven proof.
7. **tenant-portal `/staff/*` routes** appear to duplicate some of
   `mobile/staff-app`'s surface (an embedded staff-facing web view within
   the tenant-portal app) — flagged for a future round's duplication
   review (Workstream 1 follow-up), not resolved this round.
8. Workstreams 3, 4 (full), 7, 8, 10, 11, 13, 14, 15, 16 (full), 18
   (expanded), 20 (expanded) not reached this round — see each workstream's
   own doc file for the specific, honest reason.

## Round 2

9. **super_admin now VERIFIED** (resolves limitation #1 above) —
   `admin@serviceos.local`/`Password123!`, found in
   `scripts/seed_demo_users.py`. See `super-admin-access-investigation.md`.
10. **`offering_type_id` root cause now fully diagnosed** (extends
    limitation #2): `master_services.is_type_required = False` for
    `ac_repair` despite its pricing rules being 100% type-scoped — a real
    catalog-data inconsistency, not a code bug. See
    `offering-type-contract-defect.md` and
    `backend-remediation-ticket-offering-type.md`. Still not fixed (backend
    remediation explicitly out of scope this round).
11. **`GET /v1/provider/service-jobs/assignable` returns `500` for a
    customer-role token instead of `403`** — a real, backend-owned
    authorization-boundary defect discovered this round (should reject the
    role before attempting tenant-derivation logic). Not fixed (backend,
    out of scope). See `role-entry-verification.md`.
12. **Technician token can read `GET
    /v1/provider/service-jobs/assignable` for its own tenant** — an
    ambiguous finding, not confirmed as a defect (only a read was tested,
    not the mutating `assign` action). See `role-entry-verification.md`.
13. **Real React-version-pin mismatch** between
    `frontend/tenant-portal` (`19.2.7`) and `frontend/super-admin`
    (`19.2.0`) causes a duplicate-React-instance bug breaking 3 of
    tenant-portal's 16 test suites (`Invalid hook call`). Not fixed this
    round — see `frontend-corrections-report.md` for why a version-pin
    change was judged too risky to make without full rebuild verification
    within this round's time budget.
14. **`frontend/super-admin` has no wired `test` script and no jsdom vitest
    config**, despite 4 real test files existing — a real, pre-existing
    test-infrastructure gap, not fixed this round.
15. **Demo tenant's onboarding-checklist state (`0` items,
    `progress_percent:0`) is inconsistent with its real operational status**
    (has a real, active `ServiceJob`) and its package assignment shows
    `status:"pending_review"` with no `approved_at`/`activated_at` — most
    likely because this tenant was seeded directly rather than progressed
    through the real registration/approval pipeline. NOT confirmed as a
    live marketplace-activation-bypass bug in the real pipeline (a
    brand-new tenant was not registered end-to-end to test this) — see
    `tenant-onboarding-live-verification.md`.
16. **No Playwright/browser-level evidence gathered in Round 2 either** —
    all Round 2 verification (role boundaries, pricing continuity) is API-
    level curl evidence, same limitation class as Round 1's #6.
17. Workstreams 14 (visual evidence, beyond what's already noted),
    full Playwright suites, and the new targeted tests requested by the
    brief (Workstream 13) were not completed this round — see
    `deferred-workstreams.md`.
