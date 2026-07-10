# HS0 — Markdown Report Cleanup Report

## Scope and method
221 markdown report files exist at repo root, accumulated across the
entire multi-sprint session history. Given HS0's cleanup mandate,
this pass focused specifically on the Home-Services-pricing/bargain
lineage (the area this sprint's ticket is about), rather than an
exhaustive per-file audit of all 221 files — that would be a full
documentation-archaeology project on its own. Files outside that
lineage (Admin A1-A11 series, P0 Enterprise series, Sprint 1-38 series,
Phase 0A-0E series, etc.) were left in place: they document real,
still-relevant certified work and are referenced from `MEMORY.md`.

## Archived (moved to `docs/archive/obsolete/`)

| File | Why obsolete |
|---|---|
| `BARGAIN_MODULE_REMAINING_BLOCKERS.md` | Documents blockers for the old manual bargain-rules module, which has since been deactivated in favor of the symmetric auto-price-options architecture (see `MANUAL_BARGAIN_MODULE_DEACTIVATION_REPORT.md`, kept) |
| `BARGAIN_MODULE_TEST_RESULTS.md` | Test results for the same deactivated module |
| `PHASE_3C_BARGAIN_FRONTEND_REPORT.md` | Frontend certification for the old 5-step bargain wizard UI, since restructured (see `HS0_TEST_FILE_CLEANUP_REPORT.md` — `test_bargain_wizard_has_five_steps` was updated to reflect the new 6-step structure) |

Moved rather than deleted, per the ticket's stated preference ("Move old
reports to docs/archive/obsolete/. Only hard delete if project standard
allows it" — no such standard exists in this repo, so archived).

## Kept (still relevant, current architecture)

- `MANUAL_BARGAIN_DEACTIVATION_FINAL_REPORT.md`,
  `MANUAL_BARGAIN_MODULE_DEACTIVATION_REPORT.md` — these document *why*
  and *how* manual bargaining was turned off, which is exactly the
  institutional context needed to understand why bargain-related UI is
  deprecated today. Deleting these would remove the explanation for the
  very cleanup this sprint performed.
- `HOME_SERVICES_MENU_ORGANIZATION_REPORT.md`,
  `HOME_SERVICES_MENU_PRICE_RANGE_API_MAPPING_REPORT.md`,
  `HOME_SERVICES_MENU_PRICE_RANGE_REMAINING_BLOCKERS.md`,
  `HOME_SERVICES_MENU_PRICE_RANGE_TEST_RESULTS.md`,
  `HOME_SERVICES_PRICE_RANGE_VALIDATION_REPORT.md` — current, accurate
  architecture reports for the live Home Services pricing system.
- All `ADMIN_A*`, `P0_*`, `SPRINT*` certification reports — current
  certified work, referenced from `MEMORY.md`, out of this sprint's
  Home-Services-pricing-specific scope.

## Not yet reviewed (flagged, not hidden)
See `HS0_MANUAL_REVIEW_FILES.md` for the list of files whose
relevance/obsolescence could not be confidently determined within this
sprint's scope.

## Verdict
MD cleanup: **partial, scoped to the pricing/bargain lineage** the ticket
is actually about. Full 221-file audit is out of scope for one sprint;
documented as a remaining blocker for a dedicated future documentation
cleanup pass.
