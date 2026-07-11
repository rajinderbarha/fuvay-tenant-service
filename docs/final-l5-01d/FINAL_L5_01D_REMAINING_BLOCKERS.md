# FINAL-L5-01D — Remaining Blockers

## The one hard blocker to unconditional READY
**Technician redirect stability is not proven.** The specific diagnosed bug (full-page reload + dev-mode HMR interference) is fixed and verified correct in isolation (2,756ms clean transition, full real-data landing confirmed via detailed capture), but a 5-run repeated-login batch showed only 1/5 succeeding within 15s. Account lockout was ruled out. The second contributing factor is not fully root-caused. Per the mission's explicit rule 12 ("Do not mark FINAL-L5-01 READY with any inconclusive required check") and rule 7 ("Do not mark Technician redirect stable based on one successful run"), this alone prevents an unconditional READY.

## Real findings, not fixed this sprint (documented, not hidden)
1. **Service Areas "+ Add Zone" button not gated for Tenant Read Only** (L5-01D-005) — backend still blocks the actual mutation (403 confirmed), so no security exposure, but a real UX gap outside this sprint's Jobs/Bookings scope.
2. **Embedded-error pattern (200 + `success:false`) instead of HTTP 403/404** on customer booking cross-access and missing-booking cases (L5-01D-006) — no data leak, an API-consistency item.
3. **Tenant Jobs list/detail no longer show resolved names** (customer name, service type, brand, technician name) — the canonical endpoint only returns raw IDs; the migration honestly displays short IDs rather than fabricating names. Real follow-up: enrich the canonical endpoint or add client-side resolution.
4. **Legacy quote/checklist/assessment workflow removed from Job Detail** — no canonical equivalent exists; if this functionality is still required for Home Services, it needs a proper design pass.
5. **`staff/[id]/page.tsx`'s "recent jobs" widget still uses the legacy endpoint** — secondary consumer, not migrated this sprint (main Jobs pages were the mission's explicit target).
6. **Customer/Technician soft-block on Tenant Jobs / Customer Bookings endpoints** — both return safe empty results (200) rather than an explicit 403 when accessed by the wrong role; zero data leakage confirmed, but doesn't match the mission's literal expected status code.
7. **Duplicate `service_setup_templates` router mount** (carried from FINAL-L5-02) — still deferred pending consumer audit.
8. **~190-table missing-FK gap** (carried from FINAL-L5-01B) — still tracked, not remediated by design.

## Genuinely resolved this sprint (real evidence, not claims)
- Tenant Jobs canonical API migration — live + browser verified.
- Customer Booking source-of-truth decision and seed alignment — live + browser + repeatability verified.
- Tenant Read Only UI precision (Jobs pages) — root cause fixed (role persistence + string match), live + browser verified.
- Tenant Read Only backend precision — 403-before-422 confirmed on 2 endpoints.
- Full-stack repeatability — proven across a 5th cycle with zero drift.
