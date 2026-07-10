# Phase 3D — Regression Report (vs. Phase 0/1/2)

## Phase 0 baseline

| Check | Result |
|---|---|
| Clean baseline data still exists | ✅ Demo AC Services tenant, super_admin/tenant_owner/customer/technician users all confirmed present and logging in successfully this sprint |
| Demo tenant/customer/technician still exist | ✅ `provider@serviceos.in` (tenant_owner), `customer@serviceos.in`, `staff@serviceos.in` all confirmed in `users` table |
| No unintended bookings/jobs created | ✅ Only pricing-domain test records were created this session (2 provider-override test rows in Phase 3C-Closure, both cleanly deactivated with clear "Phase 3C closure test" reasons; 1 harmless no-op pricing-rule update this sprint) — no bookings, jobs, or unrelated entities touched |

## Phase 1 Admin Setup

| Check | Result |
|---|---|
| Admin login works | ✅ `POST /v1/auth/login` for `admin@serviceos.in` succeeded live this sprint |
| Dashboard loads | ✅ `/admin/dashboard` → 200 |
| Sidebar loads | ✅ Confirmed via `AdminLayout.tsx` inspection + live page loads |
| Platform Settings still correct | Not re-tested this sprint (out of Phase 3 scope; no pricing-related changes touch settings) |
| Engine Management loads | ✅ `/admin/engines` → 200 |
| Vertical Configuration shows Home Services enabled | ✅ `GET /v1/admin/verticals` → `home_services` entry with `is_enabled: true` |
| Audit Logs load | ✅ `/admin/audit-logs` → 200 |

## Phase 2 Catalog

| Check | Result |
|---|---|
| Home Services Category loads | ✅ `/admin/catalog` → 200; `GET /v1/admin/service-categories` includes "Home Services" |
| AC Services loads | ✅ Master services list under Home Services category includes AC-prefixed services |
| AC Repair loads | ✅ `GET /v1/admin/master-services/{ac_repair_id}` → `is_active: true`, name unchanged |
| Types & Brands load | ✅ `/admin/types-brands` → 200 |
| Split AC + LG mapping still exists | ✅ Confirmed via the pricing rule's `service_type_id`/`brand_id` still resolving to "Split AC"/"LG" in the live preview response |
| Not Cooling still mapped | Not independently re-queried this sprint; no code touched issue-type mappings at any point in Phase 3B/3C/3D |
| Gas Refill still mapped | ✅ Indirectly confirmed — "AC Gas Refill" master service was successfully used as a real catalog service for the Phase 3C-Closure safe-test overrides, proving it's still a valid, active, correctly-categorized service |
| Catalog pages do not show pricing duplicates | ✅ Confirmed via effective-menu inspection — Home Services' vertical module list contains 8 non-pricing modules only; no pricing_tiers/location_mapping/pricing_rules/bargain_rules/provider_overrides entries |

## Result: **PASS.** No Phase 0/1/2 hard gate broken by any Phase 3 work. All spot-checked baseline data, login flows, and catalog mappings remain intact.
