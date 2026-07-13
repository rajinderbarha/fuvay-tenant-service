# FINAL-L5-05AK — Admin Categories Runtime Repair, Critical-Route Spec Stabilization and High-Risk Action Registry Completion

## Baseline

| Item | Value |
|---|---|
| `git rev-parse HEAD` (start) | `50ba6f9` |
| `git rev-parse origin/master` (start) | `50ba6f9` (identical) |
| Backend/frontend | already running from prior sprint at start; backend restarted once (necessary to load the fix) |
| `FINAL-L5-05AJ` status | `PARTIAL_READY_WITH_FINAL_L5_05AJ_BLOCKERS` (accepted, not reinterpreted) |

## 1. `GET /v1/admin/categories` — root cause, fix, live verification

**Root cause** (isolated by direct Python reproduction, not guessed): `category_runtime_router.py`'s `list_categories` sorted results via `enriched.sort(key=lambda c: (c.get(sort_key) or ""), reverse=reverse)`. The real seeded "Home Services" category has `display_order == 0` — a valid, falsy value the `or ""` fallback incorrectly treated as "missing," substituting an empty string and mixing `int`/`str` in one sort comparison. This fires on every call using the endpoint's own default `sort_by="display_order"`, i.e. every real caller, unconditionally — confirmed reproducing the exact `TypeError` directly against real seeded data before the fix.

**Fix**: explicit `is not None` check with a type-appropriate default (`0` for `display_order`, `""` for string sort keys) replacing the truthy/falsy fallback.

**Live verification** (real backend, real PostgreSQL, real HTTP):
- `GET /v1/admin/categories` → `200`, 14 real categories, correctly sorted (`display_order=0` category first).
- All 5 canonical roles tested directly: `200` for `super_admin`, `admin_operations`, `admin_finance`, `admin_security`, `admin_readonly` (this endpoint has no role-based restriction — confirmed pre-existing, not weakened by this fix).
- `sort_by=name&sort_dir=desc` → `200`. Empty-filter query (`q=nonexistentcategoryxyz`) → `200`, empty `items` array, not an error.

**Regression tests**: 4 new real, live-database tests added to `tests/test_p0_enterprise_categories.py` (previously 100% static source-inspection — exactly how this bug went undetected for so long): a real service-call success test, a test documenting the exact real-data precondition (`display_order=0` row exists), the direct regression test against the fixed sort, and a test that documents the old buggy behavior still raises `TypeError` against real data (so a future accidental revert is caught immediately). Full file: **73/73 passing**.

## 2. CORS-masking secondary concern — investigated, no separate fix needed

Direct `curl -i` verification (with a real `Origin` header) of a controlled 404, a controlled 422, and an OPTIONS preflight request all correctly returned `access-control-allow-origin`/`access-control-allow-credentials`/`access-control-expose-headers`. The registered `@app.exception_handler(Exception)` relies on `CORSMiddleware` to apply headers after the fact, and this was verified to work correctly for every controlled error path tested. Since the only known reproducible trigger for a genuine unhandled 500 was the categories bug (now fixed), this resolves as a consequence of the primary fix — no separate CORS-handling code change was made or needed.

## 3. Critical-route 14-test spec — stabilized to 14/14, twice consecutively

Of the original 3 failures: 1 (`/admin/onboarding/providers`) was a direct symptom of the categories bug — fixed as a natural consequence of the root-cause fix, not a separate test change. The other 2 (login timeouts) did not reproduce after the backend restart the categories fix required — consistent with FINAL-L5-05AH's documented dev-server/session-instability finding; no test code changes were needed for these.

**Live result: 14/14 passed, twice consecutively** (1.7–2.3 minutes per run).

## 4. High-risk action registry — expanded from 9 to 19

10 new actions added with real endpoint + permission evidence, each read directly from router source (not re-derived from memory): Offering suspend/reactivate/readiness-refresh (`tenant_engine/admin_router.py`), User invite/invite-revoke/suspend/unsuspend/deactivate/reactivate/lock/unlock/role-change/password-reset/session-listing (`auth/platform_users_router.py`), Customer session revoke-all (`auth/admin_customers_router.py`).

## Regression evidence

Full backend suite: **9311 passed** (9307 baseline + 4 new categories tests), 1 skipped, 0 failed.

## What this sprint deliberately did not attempt (honest scope boundary)

Per this mission's own explicit framing: full five-role matrices for the 7 routes covered in FINAL-L5-05AJ (only Super Admin + Read Only tested there and here), the remaining ~10 undiscovered high-risk action types, cross-tenant/responsive/accessibility/permission-loading Chromium matrices, screen-reader certification, and the full route/action/role-denial coverage guards (only the existing route-coverage guard from FINAL-L5-05AI was re-usable; a dedicated action-registry guard was not built this sprint) remain real, substantial future work — not fabricated as complete.

## Files changed

- `app/engines/admin_catalog/category_runtime_router.py` (sort-key fix)
- `tests/test_p0_enterprise_categories.py` (4 new real regression tests)
- `docs/final-l5-05/FINAL_L5_05AI_ROUTE_ACTION_COVERAGE_REGISTRY.md` (action registry expanded 9→19)
- `docs/final-l5-05/FINAL_L5_05_BUG_REGISTER.md` (L5-05AK-001 through 004 appended)

## Final recommendation

**`PARTIAL_READY_WITH_FINAL_L5_05AK_BLOCKERS`**

This sprint closed a real, CRITICAL, previously-undiscovered backend defect with full root-cause evidence, a verified fix, live cross-role verification, and new regression tests closing the exact detection gap that let it slip through. As a direct consequence, the critical-route spec is now genuinely stable at 14/14 across two consecutive clean runs. The high-risk action registry more than doubled with real, source-verified entries. The mission's much larger remaining scope — full five-role matrices, cross-tenant/responsive/accessibility/permission-loading certification, and the remaining ~10 action types — is honestly deferred, not fabricated as complete.
