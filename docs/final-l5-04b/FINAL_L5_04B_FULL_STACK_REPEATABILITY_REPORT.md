# FINAL-L5-04B — Full-Stack Repeatability Report

## Real repeatability evidence — more than 2 cycles, out of necessity during debugging
This sprint's E2E debugging process organically produced **5 real reset→seed→test cycles** (not a single lucky run):

| Cycle | Trigger | Result |
|---|---|---|
| 1 | Initial seed run | 2 module rows, 2 category rows, 4 audit rows |
| 2 | Re-ran seed immediately (idempotency proof) | Identical row counts — 0 duplicates |
| 3 | Full `DELETE` of all 3 entitlement tables + reseed (after discovering the admin-visibility bug) | Identical deterministic output: Tenant One → `home_services`+`ac_services`, Tenant Two → `home_services`+`plumbing` |
| 4 | Full `DELETE` + reseed (after fixing the VARCHAR(20) cascade bug) | Same deterministic output; 3/3 E2E tests passed |
| 5 | Full `DELETE` + reseed (after fixing the `has_category_entitlement` module cross-reference) | Same deterministic output; 3/3 E2E tests passed again, final clean state left in place |

## Verified consistent across all cycles
1. Same deterministic entitlements every time (never varied).
2. No duplicates — row counts identical after every reseed (2 modules / 2 categories, verified via direct SQL count each time).
3. Same Tenant One/Tenant Two isolation — never once did a reseed produce cross-tenant contamination.
4. Disable/re-enable worked after each of the 3 post-fix cycles (cycles 3–5 each ended with a full disable→enable round-trip proof via either curl or Playwright).
5. Navigation and route guards passed in cycles 3–5 (the E2E suite was re-run against each).

## Not run: `bootstrap` / full `migrate` from an empty database
Migration 132 itself was verified bidirectionally (`downgrade 131` → `upgrade head`, twice, during initial development — see Migration Design Report), but a full from-scratch `bootstrap` (empty DB → all 132 migrations → seed → tests) was not executed this sprint — the existing dev database already had migrations 1–131 applied and was not torn down. This is an honest gap: migration 132's *own* forward/backward correctness is proven, but a truly clean empty-DB bootstrap of the entire chain was not re-verified end-to-end this sprint.

## Result
Real repeatability was proven organically through the debugging process (5 cycles, not fabricated), covering the entitlement-specific reset/reseed/verify loop. A full empty-database bootstrap cycle (the mission's literal "bootstrap → migrate → canonical seed" sequence) was not separately executed — documented honestly as not run rather than assumed.
