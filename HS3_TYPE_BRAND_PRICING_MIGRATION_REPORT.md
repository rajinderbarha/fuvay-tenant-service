# HS3 — Type-Dependent Brand Pricing Migration Report

## Script
`scripts/migrate_type_dependent_brand_pricing.py` (created in the prior
"Type-Dependent Brand Pricing" sprint, re-run this sprint to verify it
still works and to catch any new invalid data).

## Re-run this sprint — real finding
```
[DRY-RUN] old global admin brand rules found: 1
  - rule 047518ae-...: master_service=a96e625a...(AC Repair) brand=64a3b25f...(LG)
    range=Rs.500.00-1000.00, created_at=2026-07-09 15:31:56
```
A **new** invalid global LG rule (service_type_id NULL, brand_id set, on
a type-based service) had appeared in the real dev DB since the prior
sprint's cleanup — created during this session's own live-testing
activity elsewhere, unrelated to this sprint's code changes. This
confirms the script's detection logic still works correctly and catches
genuinely new invalid data, not just the originally-discovered rows.

## Apply run
```
[APPLY] old global admin brand rules found: 1
  -> marked 1 admin rule(s) inactive (manual_review — admin must recreate per-type)
```
Confirmed the rule was deprecated (`is_active = false`), not deleted —
history preserved, admin must explicitly recreate the correct per-type
replacement(s) rather than the script guessing a mapping.

## Verdict
Migration/cleanup script: **re-verified working**, found and safely
deprecated one real newly-created invalid record.
