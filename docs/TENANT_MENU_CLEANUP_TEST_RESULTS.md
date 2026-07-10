# Tenant Menu Cleanup — Test Results

## Test Suite: test_tenant_menu_cleanup.py

**Run date:** 2026-07-09
**Result:** 27 passed / 0 failed

| Test | Result |
|------|--------|
| test_setup_group_present_in_tenant_layout | ✅ |
| test_setup_checklist_in_nav | ✅ |
| test_business_profile_in_nav | ✅ |
| test_service_areas_in_setup_group | ✅ |
| test_service_setup_in_nav | ✅ |
| test_availability_in_nav | ✅ |
| test_service_pricing_setup_not_in_nav | ✅ |
| test_pricing_setup_not_in_nav | ✅ |
| test_customer_price_preview_not_in_nav | ✅ |
| test_bargain_settings_not_in_nav | ✅ |
| test_bargain_rules_not_in_nav | ✅ |
| test_manual_bargain_setup_not_in_nav | ✅ |
| test_old_pricing_route_shows_deprecated_message | ✅ |
| test_old_pricing_route_has_cta | ✅ |
| test_customer_price_preview_route_shows_deprecated_message | ✅ |
| test_tenant_setup_services_route_deprecated | ✅ |
| test_service_setup_has_provider_price_range | ✅ |
| test_service_setup_has_low_mid_high_preview | ✅ |
| test_no_forbidden_labels_in_tenant_layout | ✅ |
| test_no_forbidden_labels_in_nav_config | ✅ |
| test_no_forbidden_labels_in_service_setup | ✅ |
| test_service_setup_pricing_uses_safe_fallback | ✅ |
| test_nav_config_setup_group_has_correct_items | ✅ |
| test_nav_config_no_old_pricing_items | ✅ |
| test_nav_config_pricing_route_maps_to_service_setup | ✅ |
| test_finance_group_uses_correct_labels | ✅ |
| test_coverage_group_removed_from_nav | ✅ |

## TypeScript

```
cd frontend/tenant-portal && npx tsc --noEmit
Exit code: 0  — no errors
```
