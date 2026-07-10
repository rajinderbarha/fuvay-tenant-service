# HS0 — File Inventory Report (Home Services pricing/menu scope)

Full repo-wide inventory (thousands of files across `tests/`, `docs/`,
frontend pages/components, backend routers/services) is impractical to
enumerate exhaustively in one sprint report. This inventory covers every
file this sprint actually touched or classified, per file, per the
required columns.

| file_path | file_type | purpose | related module | decision | reason |
|---|---|---|---|---|---|
| `frontend/tenant-portal/components/layout/TenantLayout.tsx` | frontend component | Live tenant sidebar nav | Home Services menu | KEEP (edited) | Real duplicate-menu-item source; fixed in place |
| `frontend/tenant-portal/lib/nav-config.ts` | frontend config | Secondary nav config (not live-rendered) | Home Services menu | KEEP (edited) | Kept in sync with TenantLayout.tsx for consistency; see `HS0_MANUAL_REVIEW_FILES.md` for the unresolved dual-source issue |
| `frontend/super-admin/lib/nav-config.ts` | frontend config | Secondary nav config (not live-rendered) | Home Services menu | KEEP (edited) | Same — added matching Home Services group for consistency |
| `frontend/super-admin/components/layout/AdminLayout.tsx` | frontend component | Live admin sidebar nav | Home Services menu | KEEP (read only) | Already correct; no changes needed |
| `frontend/tenant-portal/app/(tenant)/tenant/setup/services/page.tsx` | frontend page | Canonical Service Setup wizard | Home Services setup | KEEP | Real, current, 1268 lines |
| `frontend/tenant-portal/app/(tenant)/provider/service-setup/page.tsx` | frontend page | Superseded duplicate wizard | Home Services setup | KEEP (deprecated) | Real functionality (715 lines), still reachable directly; added "moved" banner rather than deleting |
| `frontend/tenant-portal/app/(tenant)/provider/pricing/page.tsx` | frontend page | Superseded duplicate pricing form | Home Services pricing | KEEP (deprecated) | Added "moved" banner; removed from live nav |
| `frontend/tenant-portal/app/(tenant)/provider/customer-price-preview/page.tsx` | frontend page | Price preview (forbidden nav label) | Home Services pricing | KEEP (deprecated) | Added "moved" banner; removed from live nav |
| `frontend/tenant-portal/app/(tenant)/provider/services/page.tsx` | frontend page | 9-line redirect stub → `/provider/offerings` | Home Services setup | KEEP | Pre-existing, functioning redirect, unrelated to this sprint's cleanup |
| `frontend/super-admin/app/admin/pricing-rules/page.tsx` | frontend page | Deprecated global pricing page | Pricing (common) | KEEP (already deprecated) | Deprecation banner already present from an earlier sprint |
| `frontend/super-admin/app/admin/pricing/bargain-rules/page.tsx` | frontend page | Deprecated bargain wizard | Pricing (common) | KEEP (already deprecated) | Deprecation banner already present; step-label test updated |
| `frontend/super-admin/app/admin/pricing/page.tsx` | frontend page | City-tier floor price config | Pricing (common) | KEEP | Legitimate, separate, vertical-agnostic feature — not a duplicate |
| `frontend/super-admin/app/admin/catalog/page.tsx` | frontend page | Master service catalog | Catalog | KEEP | Old manual per-service pricing form already removed from this page in an earlier sprint (confirmed via grep — 0 matches for `isFixed` etc.) |
| `scripts/cleanup_home_services_test_state.py` | new script | Stale test-data cleanup | Home Services data hygiene | KEEP (new) | Created this sprint |
| `tests/test_tenant_menu_cleanup.py` | test | Tenant menu/route cleanup certification | Home Services menu | KEEP (edited) | 8 stale assertions updated to match current canonical routes |
| `tests/test_deactivate_manual_bargain_auto_price_options.py` | test | Auto price options certification | Home Services pricing | KEEP (edited) | 1 stale assertion inverted (nav item now correctly absent) |
| `tests/test_p0_tenant_service_setup_wizard.py` | test | Tenant service setup wizard certification | Home Services setup | KEEP (edited) | 1 stale nav-target assertion updated |
| `tests/test_home_services_menu_and_price_range.py` | test | Menu + price range certification | Home Services pricing | KEEP (edited) | 2 long-standing stale assertions fixed (genuinely resolved, not just documented) |
| `tests/test_phase3_pricing_rules_certification.py` | test | Pricing rules sidebar certification | Pricing (common) | KEEP (edited) | 1 stale assertion updated (Bargain Rules correctly absent from sidebar now) |
| `tests/test_phase3c_frontend_certification.py` | test | Bargain wizard frontend certification | Pricing (common) | KEEP (edited) | 1 stale assertion updated (6-step structure) |
| `tests/test_tenant_home_services_service_setup_wizard.py` | test | Old wizard-UI certification | Home Services setup | KEEP (edited) | 16 of 37 obsolete frontend-structure assertions updated/removed; 21 valid backend/migration assertions preserved |
| `tests/test_tenant_home_services_vertical_detection_fix.py` | test | Vertical detection guard certification | Home Services setup | KEEP (edited) | 3 of 17 obsolete assertions updated to match current error-handling structure |
| `tests/test_tenant_service_coverage_enterprise_ui.py` | test | Service coverage UI certification | Home Services setup | KEEP (edited) | 1 stale assertion updated (Coverage group intentionally removed) |
| `tests/test_tenant_service_setup_enterprise_wizard.py` | test | Old duplicate wizard certification | Home Services setup | KEEP (edited) | 1 stale nav-target assertion updated |
| `tests/test_dynamic_pricing_form.py` | test | Catalog dynamic pricing form certification | Catalog/Pricing | KEEP (edited) | 11 of 46 tests deleted (obsolete manual pricing form removed from `/admin/catalog`); 35 valid tests preserved |
| `tests/test_finance_package_pricing_fix.py` | test | Finance/package pricing certification | Catalog/Pricing | KEEP (edited) | 2 tests deleted (same obsolete form); remainder preserved |
| `BARGAIN_MODULE_REMAINING_BLOCKERS.md` | report | Old bargain module blockers | Pricing (obsolete) | ARCHIVE | Moved to `docs/archive/obsolete/` |
| `BARGAIN_MODULE_TEST_RESULTS.md` | report | Old bargain module test results | Pricing (obsolete) | ARCHIVE | Moved to `docs/archive/obsolete/` |
| `PHASE_3C_BARGAIN_FRONTEND_REPORT.md` | report | Old 5-step bargain wizard certification | Pricing (obsolete) | ARCHIVE | Moved to `docs/archive/obsolete/` |

For files outside this direct-touch list (the remaining ~215 root
markdown reports, and the broader `tests/`/`docs/` tree beyond the
Home-Services-pricing lineage), see `HS0_MANUAL_REVIEW_FILES.md` —
flagged as not individually reviewed this sprint rather than silently
assumed clean.
