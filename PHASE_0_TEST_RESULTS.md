# Phase 0 — Test Results

## Backend test command

```bash
pytest tests/ -q
```

(Real project convention — no `pytest.ini` custom invocation needed.)

## Backend result

**7968 passed, 37 failed, 1 skipped** (out of 8006 collected).

All 37 failures are **pre-existing and unrelated to this sprint** — confirmed
by cross-referencing against the exact same 37/38-failure baseline
independently established in Phase 1 and Phase 2 of this certification
(catalog/pricing-form/brand-flow frontend-assertion tests expecting page
content that predates this session's nav-config refactor by a concurrent
process). No new failures were introduced by the Phase 0 cleanup or seed.

**One real regression was caused and fixed within this same sprint**: deleting
the `admin@serviceos.local` user (flagged as a "duplicate" in the cleanup
step) broke 24 pre-existing integration tests
(`test_trust_quality_phase1.py`, `test_p0_sidebar_duplicate_cleanup.py`) that
hardcode that exact email in their auth fixtures. Found via this same full
suite run, the account was restored (same role/password), and a re-run
confirmed all 24 tests pass again — see `DATA_CLEANUP_AUDIT.md` for the
correction note. The final 37-failure count above is **after** that fix.

## Frontend TypeScript result

```bash
npx tsc --noEmit
```

**0 errors.**

## Frontend lint result

```bash
npx next lint
```

**Broken, pre-existing** (not caused by this sprint) — Next.js 16 removed the
`next lint` subcommand entirely; running it now parses `lint` as a project
directory argument and fails with `Invalid project directory provided, no
such directory: .../lint`. No working lint command exists in this repo.
Documented honestly per the ticket's explicit instruction not to hide this.

## Frontend test result

No `test` script exists in `frontend/super-admin/package.json` (only
`dev`/`build`/`start`/`lint`). No JS test runner (jest/vitest) is configured
anywhere in the repo. This repo's established convention (used across every
prior sprint in this session) is Python source-inspection tests under
`tests/*_frontend.py`, run via the same `pytest` command above.

## Known pre-existing failures (37, unrelated to Phase 0)

- `test_admin_tenant_stabilization.py` (5) — expects hardcoded nav items that
  moved to `nav-config.ts` in a concurrent process's refactor
- `test_brand_flow_improvements.py` (8) — expects old Types & Brands tab
  content superseded by the newer `/admin/types-brands` enterprise page
- `test_dynamic_pricing_form.py` (11) — expects a pricing form component
  structure that predates a later pricing UI refactor
- `test_finance_package_pricing_fix.py` (2) — same category
- `test_p0_provider_enterprise.py` (2) — expects specific onboarding link
  text/component names not present in the current page content
- `test_sprint34a_ui_foundation.py` (1), `test_sprint34c_master_data.py` (6),
  `test_sprint38_universal_catalog.py` (1) — expect nav/page structure that
  predates later navigation consolidation sprints

## New failures caused by this sprint

**None**, after the `admin@serviceos.local` restoration described above.
