# FINAL-L5-01B — Canonical Rule Seed Report

## Run 1 (fresh)
```
[VERIFY] 4 active health_formulas
[VERIFY] 5 active badge_rules
[CREATE] recommendation_rule: Provider-First Home Services Matching (global scope)
[CREATE] notification_channel_config: email/sms/push/in_app for Demo AC Services (4 rows)
[SUMMARY] {'health_rules_verified': 4, 'badge_rules_verified': 5, 'matching_rules': 1, 'notification_channel_configs': 4}
```

## Run 2 (idempotency)
```
[SKIP] recommendation_rule: Provider-First Home Services Matching (exists)
[SKIP] notification_channel_config x4 (exist)
[SUMMARY] {'health_rules_verified': 4, 'badge_rules_verified': 5, 'matching_rules': 0, 'notification_channel_configs': 0}
```

## Verification against required checklist

| Requirement | Result |
|---|---|
| Deterministic | Yes — stable keys (`code`, `(tenant_id, channel)`) |
| Idempotent | Yes — proven via 2 consecutive runs, run 2 = 100% skips |
| Transaction-safe | Yes — single commit per script run, no partial state on success |
| Stable lookup keys | Yes |
| 0 duplicate rule rows | Confirmed — `SELECT code, count(*) FROM recommendation_rules GROUP BY code HAVING count(*)>1` = 0 rows |
| 0 duplicate active versions | N/A — no versioned rule domain was created this sprint (matching rule and notification config are both single-version) |
| Same stable keys | Confirmed — identical `code`/`channel` values across both runs |
| Same effective rule state | Confirmed — `status='active'` unchanged |
| Same deduction behavior | Confirmed — deduction rule is embedded in `service_pricing_rules` (FINAL-L5-01), untouched by this script, still `-21`/`-15` |
| No manual post-seed SQL | Confirmed — no manual SQL was run outside the script |
| No invalid overlapping effective periods | N/A — no `effective_from`/`effective_to` fields used by the domains actually seeded |

**Result: PASS.**
