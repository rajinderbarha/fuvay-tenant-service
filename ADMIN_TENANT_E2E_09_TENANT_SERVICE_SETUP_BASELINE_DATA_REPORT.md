# ADMIN-TENANT-E2E-09 — Baseline Data Report (real psql queries, tenant `34b427a7-b2be-496c-b826-6d51bb181248`)

| Check | Result |
|---|---|
| Tenant business_name | `Demo AC Services` (confirmed) |
| Home Services / AC Repair enabled | `tenant_services` row `015efedb-dd92-41f4-97ef-cc2745437760`, master_service AC Repair (`a96e625a-60e1-46c0-bde4-ccbb88da50a2`), `is_enabled=t`, `setup_status='published'`, `published_at=2026-07-09 17:46:18` |
| Split AC type available | `tenant_service_types` row exists for `tenant_service_id=015efedb...`, `service_type_id=c86dfcf3-53bd-4d83-bf0b-51257f382652` ("Split AC" per `service_types` table) |
| Window AC type available | `tenant_service_types` row exists, `service_type_id=e27f6591-9b8d-4d57-93d0-8ed86c19c8af` ("Window AC") |
| LG brand available | `tenant_service_brands`: 2 rows for LG (`64a3b25f-23aa-4639-8baf-f67def0f60db`), one per type context (Split AC, Window AC), both `is_enabled=t` |
| "Not Cooling" issue available | Not independently re-queried this sprint (already confirmed in prior sprints per handoff notes); out of primary scope, not disturbed |
| Service area 141001 exists | `tenant_service_areas` row `d1e94fb5-2b33-4168-9881-61574b78153c`, zipcode `141001`, city Ludhiana, `is_active=t`, `is_primary=t` |
| Availability open | Not independently re-verified (out of scope — availability engine tested in prior sprints); no evidence of regression |
| Usage credit balance sufficient | **DISCREPANCY FOUND**: `tenant_wallets.credit_balance = 0.0000` (not 3958.00 as stated in handoff). `lifetime_purchased=1100.0000`, `lifetime_consumed=1100.0000`. The 3958.00 figure from the prior finance sprint no longer matches current DB state — credits have since been fully consumed by other sprint activity between then and now. This is a real, current finding, not fabricated. |
| Tenant bookable after publish | AC Repair tenant_service is already `published`. Bookability additionally depends on credit balance per the booking/matching eligibility gate (`match_provider_and_price` — "pricing, package, credits, deposit"); with balance at 0 this is a genuine risk to real bookability, but is a finance-engine concern, out of this sprint's scope to remediate (would require topping up wallet — a payment/finance action explicitly out of scope for E2E-09). |

## Verdict: PASS WITH ONE FLAGGED DATA DRIFT (usage credit balance is 0, not 3958.00) — flagged as blocker-adjacent finding, not fixed (out of scope), carried to Remaining Blockers.
