# FINAL-L5-01B — Canonical Rule Seed Specification

Implemented in `scripts/canonical_rule_seed_final_l5_01b.py`. Covers only domains with a verified real schema (see rule model inventory).

| Domain | Action | Record |
|---|---|---|
| Health Rules | Verified (not re-created) | 4 pre-existing active `health_formulas` rows, e.g. `provider_business_health_default` — functionally equivalent to the mission's "Standard Provider Health Rule" |
| Badge Rules | Verified (not re-created) | 5 pre-existing active `badge_rules` rows, incl. `rule_verified_provider` — functionally equivalent to "Verified Service Provider" |
| Reward Rules | **Not seeded** — no backing table exists | NOT_SEEDABLE_NO_SCHEMA |
| Completed Job Deduction Rule | Already covered by FINAL-L5-01 | `service_pricing_rules.completed_job_deduction_credits = 21` (Split AC) / `15` (Window AC) |
| Credit Threshold Rule | **Not seeded** — no backing table exists | NOT_SEEDABLE_NO_SCHEMA |
| Matching Rule | **Created** | `recommendation_rules` row, `code='final_l5_01b_provider_first_matching'`, name "Provider-First Home Services Matching", global scope, `status='active'`, condition JSON requiring active tenant + service setup + coverage + valid pricing + supported zipcode + availability |
| Availability Policy | Already covered by FINAL-L5-01 | `provider_availability_rules`, 6 rows (Mon-Sat) |
| Service Area Policy | Already covered by FINAL-L5-01 | `tenant_service_areas`, 141001 active |
| Provider Verification Rule | **Not seeded** — no backing table exists | NOT_SEEDABLE_NO_SCHEMA |
| Notification Policy | **Created** (best-effort substitute) | 4 `notification_channel_configs` rows for Demo AC Services (email/push/in_app enabled, sms disabled), each carrying a `config.policy_name = "Core Booking and Operations Notifications"` payload naming the canonical event set — the closest real schema equivalent to a standalone "policy" record, since no dedicated policy table exists |

## Stable keys used
`recommendation_rules.code`, `notification_channel_configs.(tenant_id, channel)` composite — both verified idempotent via a `SELECT` existence check before insert.

## Why 4 domains are not seeded
Per the non-negotiable rule "Do not fabricate configuration records that violate existing schemas" — inventing new tables or shoehorning Reward/Credit-Threshold/Provider-Verification/standalone-Notification-Policy data into an unrelated existing table would violate this rule. These are documented as real, honest gaps in `FINAL_L5_01B_REMAINING_BLOCKERS.md`, not silently invented.
