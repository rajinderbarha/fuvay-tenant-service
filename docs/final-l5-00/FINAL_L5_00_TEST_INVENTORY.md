# FINAL-L5-00 Part 9 — Test Inventory

Read-only inventory of test files across the ServiceOS monorepo: backend pytest suites, frontend
unit/component tests, and Playwright e2e specs. File-level granularity (not per-test-function),
with approximate `def test_` counts per file group derived from grep/PowerShell enumeration.

Total backend test files: **199** (`tests/test_*.py`)
Total Playwright e2e specs: **35** (`e2e/**/*.spec.ts` = 25, `frontend/e2e-admin-tenant/e2e/**/*.spec.ts` = 10)
Frontend unit/component test files (Jest/Vitest style `*.test.ts(x)`/`*.spec.ts(x)` under app source):
**0 found** in `frontend/super-admin/{app,components,lib,hooks}` and `frontend/tenant-portal` (excl.
node_modules); `frontend/super-admin/tests/` contains 4 misplaced **pytest** files (`test_super_admin.py`,
`test_sprint26_hardening.py`, + 2 others) rather than JS/TS unit tests. `frontend/customer-app` has 1
non-node_modules test-like file. This confirms the project's test strategy is backend-pytest +
Playwright-e2e, with no dedicated frontend component-test layer.

All sampled backend tests (test_sprint38_universal_catalog.py, test_p0_admin_bookings.py) show **zero**
"mock" occurrences — this suite exercises a real DB/API stack rather than mocked units (consistent with
prior sprint memory notes). All Playwright specs are real-browser e2e by definition.

## Backend test groups (tests/test_*.py, application: FastAPI backend, type: integration, no mocks, real DB)

| Group (filename pattern) | Files | Approx `def test_` count | Classification |
|---|---|---|---|
| `test_p0_*.py` | 50 | 2524 | KEEP_ACTIVE / KEEP_CRITICAL (enterprise P0 hardening suites; core regression gate) |
| `test_sprint*.py` (numbered sprints 3–76 + lettered 34a–34l) | 37 | 2295 | KEEP_ACTIVE (chronological feature-delivery tests; still exercise live routers/models) |
| `test_phase*.py` (phase0a–e, 1–22, certification variants) | 36 | 1263 | KEEP_ACTIVE / REVIEW_REQUIRED (many "certification" phase files overlap sprint-equivalent coverage from the same era — see notes below) |
| `test_tenant_*.py` | 11 | 342 | KEEP_ACTIVE (tenant-portal enterprise UI/wizard coverage) |
| `test_admin_*.py` | 4 | 127 | KEEP_ACTIVE (admin A2/A3 dashboard + catalog certification) |
| `test_hs*.py` (Home Services HS3–HS9b) | 7 | 115 | KEEP_ACTIVE |
| `test_step*.py` (Step4–Step9, incl. `_smoke` variants) | 6 | 113 (+ smoke files counted separately, not `def test_` matched — see note) | KEEP_ACTIVE / REVIEW_REQUIRED (smoke variants `test_step6_smoke.py`…`test_step9_smoke.py` may duplicate coverage already in the numbered step files; not confirmed identical, flagged for review) |
| `test_customer_*.py` | 3 | 51 | KEEP_ACTIVE |
| `test_frontend_connect_*.py` | 1 | 15 | KEEP_ACTIVE |
| `test_ai_chat*.py` | 2 | 21 | KEEP_ACTIVE |
| Misc singletons (`test_health.py`, `test_versions.py`, `test_dispatch_job_sync.py`, `test_dynamic_pricing_form.py`, `test_media_engine.py`, `test_checklist_system.py`, `test_business_intelligence.py`, `test_platform_audit.py`, `test_public_registration.py`, `test_quote_approval.py`, `test_serviceability_*.py`, `test_service_catalog.py`, `test_service_setup_templates_ui_polish.py`, `test_staff_*.py`, `test_trust_quality_phase1.py`, `test_twilio_cloudinary_setup.py`, `test_type_dependent_brand_pricing.py`, `test_usage_quota.py`, `test_auth_login_fix.py`, `test_bargain_customer_range_platform_fee.py`, `test_brand_*.py`, `test_deactivate_manual_bargain_auto_price_options.py`, `test_finance_package_pricing_fix.py`, `test_home_services_*.py`, `test_job_type_*.py`, `test_location_pagination.py`, `test_api_call_quota.py`, `test_provider_first_matching_and_price_choice.py`) | ~43 | not individually tallied (est. 400–600 combined) | KEEP_ACTIVE (targeted bugfix/regression tests, one file per fix — matches repo convention of "P0 fix" commits) |

### Duplicate/overlap flags (backend)

- **`test_sprint34d_brands.py`** (398 lines, 70 `def test_`) vs **`test_sprint34d_brand_management.py`**
  (682 lines, 107 `def test_`) — both open with near-identical migration-056 existence/revision-chain
  tests (`test_migration_056_exists`, `test_migration_056_revision*`, brand-model/mapping-model
  existence tests) before diverging into broader coverage in the `_brand_management` file. This looks
  like two passes over the same Sprint 34D feature (one narrower, one broader), not two different
  features. Per instructions, **not auto-classified as DUPLICATE_SUPERSEDED** without stronger evidence
  of a full rewrite — flagged **REVIEW_REQUIRED** for a human to diff test bodies and confirm whether
  `test_sprint34d_brands.py` is a subset before consolidating.
- **`test_step6_job_assignment.py` / `test_step6_smoke.py`**, **`test_step7_job_type_flow.py` /
  `test_step7_smoke.py`**, **`test_step8_quote_checklist.py` / `test_step8_smoke.py`**,
  **`test_step9_billing.py` / `test_step9_smoke.py`** — each numbered step has a companion `_smoke`
  file. Smoke files are typically a fast subset (health-check style), not full duplicates, so classified
  **KEEP_ACTIVE** with a **REVIEW_REQUIRED** note rather than DUPLICATE_SUPERSEDED — did not open every
  pair to confirm scope difference.
- No other same-feature-two-files patterns found matching the `test_catalog_old.py` vs `test_catalog.py`
  style described in the task brief. Cross-referenced against root-level dedup reports
  (`ADMIN_A2_DASHBOARD_*`, `ADMIN_A3_*`, `P0_Duplicate_Category`-style docs) — those reports describe
  **application code** dedup (e.g. duplicate CategoriesTab UI), not duplicate test files; no test file
  pairs were found tied to those specific reports.

## Playwright e2e specs (application: super-admin / tenant-portal frontends via browser, type: e2e, real browser: yes)

| Group | Path pattern | Files | Classification |
|---|---|---|---|
| Super-admin e2e | `e2e/super-admin/*.spec.ts` | 14 (auth, compliance, dashboard, finance x3, location-mapping-import, marketing, operations, pricing-tiers, security x3, tenants) | KEEP_CRITICAL (primary regression gate for admin portal) |
| Tenant-portal e2e | `e2e/tenant-portal/*.spec.ts` | 11 (auth, bookings, chat, customers, dashboard, documents, finance, jobs, reviews, settings, staff) | KEEP_CRITICAL |
| Admin-tenant combined e2e | `frontend/e2e-admin-tenant/e2e/*.spec.ts` | 10 (numbered `e2e02`–`e2e11` suites: shell, catalog-pricing, matching-ops, hs-job-ops, finance-tenant, notif-audit-reports, foundation, finance-notif-settings, rbac-bookability, service-setup) | KEEP_CRITICAL — this is a **separate, later-generation e2e suite** covering similar ground (admin shell, finance, catalog) to `e2e/super-admin/*` and `e2e/tenant-portal/*`. Given the numbered/sequenced naming (`e2e02`…`e2e11`) it appears to be a purpose-built systematic pass layered on top of the earlier ad-hoc `e2e/` specs rather than a straight replacement — flagged **REVIEW_REQUIRED** to confirm whether `e2e/super-admin` + `e2e/tenant-portal` are now superseded by `frontend/e2e-admin-tenant`, but no direct file-name collisions were found to confirm exact 1:1 supersession, so no OBSOLETE_CONFIRMED classification was applied. |

## Frontend unit/component tests

No `*.test.ts(x)` / `*.spec.ts(x)` files exist under `frontend/super-admin/{app,components,lib,hooks}` or
anywhere in `frontend/tenant-portal` outside node_modules. `frontend/super-admin/tests/` holds 4 pytest
files (misnamed for a JS project; likely backend-adjacent tests colocated by mistake or intentionally
scoped to that frontend's local API layer) — classified **REVIEW_REQUIRED** (wrong-location, not
necessarily wrong-content). No GENERATED_RECREATABLE or BROKEN_TEST candidates identified in this pass
since no destructive/collection run of the frontend test runner was performed (out of scope: "do not run
full test suites").

## Classification summary

- **KEEP_CRITICAL**: all Playwright e2e specs (35 files) — these are the only real-browser regression
  coverage and are cheap in count, high in value.
- **KEEP_ACTIVE**: the large majority of backend test files (≈190 of 199) — sprint/phase/P0/step/hs/tenant/admin
  suites map 1:1 to shipped features per the sprint memory log and show no internal signs of being stale.
- **REVIEW_REQUIRED**: `test_sprint34d_brand_management.py` vs `test_sprint34d_brands.py` overlap; the four
  `test_step*_smoke.py` companion files; the `frontend/e2e-admin-tenant` vs `e2e/super-admin`+`e2e/tenant-portal`
  relationship; the 4 misplaced pytest files under `frontend/super-admin/tests/`.
- **DUPLICATE_SUPERSEDED / OBSOLETE_CONFIRMED / GENERATED_RECREATABLE / BROKEN_TEST**: none confirmed in
  this pass — no evidence met the bar for certain classification without deeper diffing than a read-only,
  time-boxed inventory pass allows. Left for a follow-up part to open and diff the flagged pairs.
