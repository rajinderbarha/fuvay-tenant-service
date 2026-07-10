# FINAL-L5-01 — Configuration Rule Data Readiness Report

## Status: NOT IMPLEMENTED this sprint — explicit gap

The mission's Part 18 asks for canonical records across 9 rule/policy categories: health rules, badge rules, reward rules, completed-job-deduction rules, credit threshold rules, matching rules, availability policy, service area policy, notification policy.

**None of these were seeded as explicit configuration rows this sprint.** The canonical seed script focused its available time budget on the higher-priority Parts 5–16 (reset, seed core entities, integrity, ledger) given the mission's own acceptance criteria weighting those as blocking (`NOT_READY_FINAL_L5_01_LEDGER_INTEGRITY_FAILED` etc. are named failure states; there is no equivalent named failure state for missing configuration-rule data, suggesting the mission itself treats this as lower-priority than the ledger/tenant-isolation/reset mechanics).

## What exists today instead
- The "Completed Job Deduction" amount (21 credits) is currently **hardcoded in the seed script** rather than read from a dedicated deduction-rule configuration table. This works for this sprint's deterministic scenario but means there is no queryable "deduction rule" record for a future admin UI to display/edit.
- `provider_availability_rules` (the actual availability policy table) IS populated — 6 rows, Mon–Sat, per-tenant scope. This substitutes for the mission's "availability policy" ask, just not framed as a separate abstract "policy" record.
- `tenant_service_areas` substitutes for "service area policy" in the same sense.

## Not found in the schema at all
A scan for tables matching "health_rule", "badge_rule", "reward_rule", "credit_threshold", "matching_rule", "notification_policy" patterns did not turn up dedicated tables during this sprint's schema inventory — these may not exist as first-class configuration tables in the current schema, or may be represented differently (e.g. as JSON config blobs on another table) than the mission assumed. Not conclusively verified either way given time constraints.

## Recommendation
Treat this as a scoped-out item for FINAL-L5-01 and a named target for a future sprint focused specifically on configuration/rules data — the mission's acceptance criterion #25 ("Configuration rule records exist") is **not met** this sprint. This is called out plainly in the final report and remaining blockers rather than claimed as done.
