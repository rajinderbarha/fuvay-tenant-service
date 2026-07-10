# Phase 0 — Idempotency Report

All seed scripts were run twice in this sprint (once during initial baseline
creation, once explicitly to verify idempotency). Row counts were compared
before/after the second run.

## Catalog seed scripts (`seed_universal_categories.py`, `seed_service_groups.py`,
## `seed_master_services.py`, `seed_brands.py`, `seed_issue_types.py`,
## `seed_ac_repair_baseline_mappings.py`)

Second-run output: **100% `[SKIP]`** on every row — 0 created, 0 duplicated.

| Table | Count (1st run) | Count (2nd run) | Match |
|---|---|---|---|
| `service_categories` | 14 | 14 | ✅ |
| `service_groups` | 62 | 62 | ✅ |
| `master_services` | 60 | 60 | ✅ |
| `service_types` | 2 | 2 | ✅ |
| `brands` | 35 | 35 | ✅ |
| `service_type_mappings` | 2 | 2 | ✅ |
| `brand_mappings` | 3 | 3 | ✅ |
| `master_issue_types` | 39 | 39 | ✅ |
| `master_service_options` | 374 | 374 | ✅ |
| `service_issue_mappings` | 20 | 20 | ✅ |
| `service_option_mappings` | 2 | 2 | ✅ |

## Phase 0 baseline seed (`seed_phase0_baseline.py`)

Second-run output: **100% `[SKIP]`**.

| Item | Count (1st run) | Count (2nd run) | Match |
|---|---|---|---|
| `pricing_tiers` (code='mid') | 1 | 1 | ✅ |
| `tier_locations` (zipcode='141001') | 1 | 1 | ✅ |
| `service_pricing_rules` (rule_code='ac_repair_split_ac_lg_ldh_141001') | 1 | 1 | ✅ |
| `service_packages` (slug='starter_home_services') | 1 | 1 | ✅ |
| `tenants` (slug='demo-ac-services') | 1 | 1 | ✅ |

## Checklist mapping to ticket's 12 items

| # | Item | Result |
|---|---|---|
| 1 | No duplicate users | ✅ (cleanup removed dupes; `admin@serviceos.local` restored once, exactly once) |
| 2 | No duplicate roles | ✅ N/A — roles are code constants, not DB rows |
| 3 | No duplicate engines | ✅ registry is static Python data, not reseeded |
| 4 | No duplicate navigation items | ✅ static-verified, unchanged from Phase 1/2 |
| 5 | No duplicate Home Services category | ✅ 1 row, confirmed |
| 6 | No duplicate AC Repair service | ✅ 1 row (slug unique constraint) |
| 7 | No duplicate Split AC type | ✅ 1 row |
| 8 | No duplicate LG brand | ✅ 1 row |
| 9 | No duplicate Not Cooling issue type | ✅ 1 row (`ac_not_cooling`); a second, differently-coded row (`not_cooling`) from an unrelated seed script was flagged as a pre-existing duplicate-concept risk in Phase 2 — not introduced or worsened this sprint |
| 10 | No duplicate ₹800 pricing rule | ✅ 1 row (unique lookup by `master_service_id`+`service_type_id`+`brand_id`+`zipcode`) |
| 11 | No duplicate package | ✅ 1 row (unique slug) |
| 12 | No duplicate tenant/customer/technician | ✅ Demo AC Services tenant: 1 row; customer/technician reused existing fixed-identifier accounts, no new rows created on re-run |

**All 12 idempotency checks pass. Reset script (`serviceos_reset_dev_data.py`)
was not re-run a second time** (deletion is inherently a one-shot operation
given it targets a specific stale row by slug — re-running it against the
now-clean state correctly reports "nothing to delete", verified via its
built-in dry-run mode).
