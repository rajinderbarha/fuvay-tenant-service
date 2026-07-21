# Known Limitations — Slice 2F-39A

1. **229 mounted routes remain genuinely unclassified**, down from 261 —
   this slice completed exactly one module (`auth.router`, 32 routes)
   with real source-level evidence out of 33 modules containing
   classifier-flagged routes. The remaining 32 modules were not
   individually inspected. Full completion at this rate would require
   roughly 7-8x the effort spent this slice.
2. **5 of the 8 newly added canonical mutations** (`invite_staff`,
   `update_permissions`, `deactivate_staff`, `resend_invite`,
   `update_staff_schedule`) were added on guard-pattern evidence only —
   no dedicated positive/negative/cross-tenant test was written for them
   this slice (unlike the 3 api-key routes, which got 4 real tests). No
   alternate-caller/service-layer-bypass grep was performed for these 5
   either (`service-layer-bypass-audit.csv` marks them UNVERIFIED on that
   dimension).
3. **`verify_2f37.py`'s hardcoded 313/313 assertions were not updated** —
   the true, evidence-backed canonical count is now 321. This is recorded
   as a reconciliation gap (`canonical-coverage-reconciliation.md`), not
   silently left inconsistent, but it was not fixed.
4. **No dedicated `verify_2f39a.py`** with the ~20 mission-specified
   negative fixtures was built.
5. Full backend regression was not re-run a second time this slice (only
   Phase-2F, twice) — see `phase2f-regression-report.md` /
   `full-backend-regression-diff.md` for what was actually run.
6. **13 pre-existing domain-logic failures, 2 frontend version-pin
   drifts, 2 TypeScript-compile checks** remain from Slice 2F-39's own
   disposition — explicitly out of this slice's scope to resolve (this
   slice owns only route census + the 2 notification tests).
