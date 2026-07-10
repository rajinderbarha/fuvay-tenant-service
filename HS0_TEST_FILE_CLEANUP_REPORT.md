# HS0 — Test File Cleanup Report

## Method
Ran the full Home-Services-adjacent test surface
(`-k "home_services or tenant_menu or bargain or pricing or provider_matching or auto_price"`),
found 34 failures across 6 files, and classified each failure as either
(a) caused by this sprint's nav/route cleanup edits (fix forward) or
(b) pre-existing drift where the test asserted structure that had already
been superseded by a later, real rewrite of the underlying page (update to
match current reality, or delete if the assertion no longer applies to
anything).

**Hard rule followed**: no test was deleted solely for failing. Every
change below is because the test asserted on removed/renamed/relocated
UI or menu structure — not because the feature it originally verified
stopped existing.

## Deletions (exact obsolete assertions removed, not whole files)

| File | Deleted | Why | Replacement |
|---|---|---|---|
| `tests/test_dynamic_pricing_form.py` | 11 tests (`test_catalog_fixed_pricing_section`, `test_catalog_range_pricing_section`, `test_catalog_post_assessment_section`, `test_catalog_hourly_section`, `test_catalog_is_form_valid_controls_submit`, `test_catalog_handle_save_sends_model_specific_fields`, `test_catalog_open_edit_loads_hourly_rate`, `test_catalog_open_edit_loads_customer_note`, `test_catalog_job_type_defaults_applied_on_change`, `test_catalog_requirement_toggles_dynamic`, `test_catalog_price_summary_per_model`) | Manual per-service pricing form (`isFixed`/`isRange`/`isPostAssessment`/`isHourly`) removed entirely from `/admin/catalog` | `/admin/home-services/pricing-rules` + `/tenant/setup/services` |
| `tests/test_finance_package_pricing_fix.py` | 2 tests (`test_catalog_master_service_pricing_helper_text`, `test_catalog_master_service_pricing_link`) | Same removed manual pricing form/helper text on `/admin/catalog` | Same as above |

35 other tests in these two files (unrelated catalog/finance behavior) were left untouched and still pass.

## Updated (assertion text/target corrected, test intent preserved)

| File | Test | Old assumption | New reality |
|---|---|---|---|
| `test_tenant_menu_cleanup.py` | `test_old_pricing_route_shows_deprecated_message`, `test_old_pricing_route_has_cta`, `test_customer_price_preview_route_shows_deprecated_message` | Deprecated pages redirect to `/provider/service-setup` | Canonical page is `/tenant/setup/services`; banners updated to point there |
| `test_tenant_menu_cleanup.py` | `test_tenant_setup_services_route_deprecated` (deleted) | Canonical page itself should show a "moved" banner | Backwards — the canonical page is the destination, not deprecated. Deleted. |
| `test_tenant_menu_cleanup.py` | `test_service_setup_has_provider_price_range`, `test_service_setup_has_low_mid_high_preview` | Checked the wrong file (`/provider/service-setup`, the superseded duplicate) | Repointed at `TENANT_SETUP_SERVICES` (the real canonical wizard) |
| `test_tenant_menu_cleanup.py` | `test_nav_config_pricing_route_maps_to_service_setup` → renamed `test_nav_config_has_no_dead_pricing_mapping` | Expected a redirect mapping to `provider-service-setup` | Feature removed outright, not redirected — mapping deleted |
| `test_tenant_menu_cleanup.py` | `test_coverage_group_removed_from_nav` | Only checked group absence | Also asserts Service Coverage still reachable (folded into Setup group, not lost) |
| `test_deactivate_manual_bargain_auto_price_options.py` | `test_tenant_nav_has_customer_price_preview_item` | Asserted the item **must** be in nav | HS0 removed it from nav (ticket-forbidden duplicate); assertion inverted |
| `test_p0_tenant_service_setup_wizard.py` | `test_nav_points_to_service_setup` | Asserted nav points at `/provider/service-setup` | Nav now points at canonical `/tenant/setup/services` |
| `test_home_services_menu_and_price_range.py` | `test_tenant_wizard_still_shows_platform_allowed_range`, `test_tenant_cannot_edit_admin_fields` | Checked for literal `"Working Range"` text and `value={min}`/`value={max}` bindings | Page was rebuilt into a per-type/brand table (`tp.tenantMin`/`tp.tenantMax` bound to `tp.adminFloor`/`tp.adminCeiling`); assertions updated to match |
| `test_phase3_pricing_rules_certification.py` | `test_sidebar_pricing_group_renamed_and_has_no_duplicates` | Expected `"Bargain Rules"` still in the common sidebar | It was removed from the live sidebar entirely (deprecated page is direct-URL-only); assertion inverted to expect 0 |
| `test_phase3c_frontend_certification.py` | `test_bargain_wizard_has_five_steps` | Expected step titled `"Bargain Policy"` | Split into `"Customer Range + Platform Fee"` and `"Legacy Fixed Floor"` steps in a later sprint |
| `test_tenant_home_services_service_setup_wizard.py` | 16 of 37 tests | Asserted on an old multi-step `WIZARD_STEPS` UI (`CatalogCard`, `TypesStep`, `PricePreviewCard`, `SectionError`, `canCreate`/`canUpdate`/`canPublish` flags, `safeCurrency`/`safePercent`) | Page was rewritten into a per-type/brand pricing table; underlying backend/migration/permission coverage (21 tests) kept unchanged and still passes |
| `test_tenant_home_services_vertical_detection_fix.py` | 3 of 17 tests | Asserted a distinct `tenant.error` branch with specific copy | `useTenant()` now self-heals on every mount with no separate error branch; updated to match current loading→guard structure |
| `test_tenant_service_coverage_enterprise_ui.py` | `test_sidebar_has_coverage_group_with_service_areas` | Expected standalone `"Coverage"` group | Group removed, item relocated into Setup (HS0 requirement); assertion updated |
| `test_tenant_service_setup_enterprise_wizard.py` | `test_route_exists_and_is_wired_into_nav` | Expected `/provider/service-setup` wired into nav | Nav now points at canonical `/tenant/setup/services`; old page still exists with a forward-pointing banner |

## Pre-existing, unrelated failures (confirmed via evidence, left as-is)

`tests/test_sprint34k_navigation.py::TestTenantNavConfig::test_has_core_group`
and `::test_provider_items` — assert on nav-config.ts structure (`"core"`
group id, `"provider-marketing"` id) that predates this session's
`nav-config.ts` schema entirely (current schema uses `"overview"`/no
per-provider-marketing id). Confirmed neither assertion touches anything
HS0 modified. Documented in `HS0_REMAINING_BLOCKERS.md`, not fixed (out
of Home Services cleanup scope — this is a general nav-config drift
issue spanning the whole nav-config.ts history).

## Result
All Home-Services-adjacent, menu, pricing, and bargain test files: **0
failures** after cleanup (was 34 + 4 caused by this sprint's own edits =
38 total addressed). 2 unrelated pre-existing failures left, documented.
