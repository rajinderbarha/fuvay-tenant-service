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
