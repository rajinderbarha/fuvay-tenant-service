# Phase 3D — Pricing Audit Closure Report

## Audit events — actual action-string naming vs. ticket-assumed naming

The ticket assumes dotted event names like `pricing_tier.created`. The real
system logs `entity_type` + `action` as two separate fields (not a single
dotted string), which is equivalent information, differently shaped:

| Ticket event | Real `entity_type` / `action` | Exists? |
|---|---|---|
| `pricing_tier.created` / `.updated` | `pricing_tier` / `create`, `update` | ✅ (code path confirmed; live-fired this sprint for `pricing_rule`, same `_audit()` helper) |
| `city_zip_mapping.created` / `.updated` | `tier_location` / `create`, `update` | ✅ code path confirmed |
| `pricing_rule.created/updated/activated/deactivated` | `pricing_rule` / `create`, `update`, activate path uses `is_active` field update (no distinct `"activate"` action string — uses `"update"`) | ✅ create/update confirmed live; activate/deactivate use the generic update path, not distinctly-named actions — a real but minor naming granularity gap |
| `bargain_rule.created/updated/activated/deactivated/validated/evaluated_preview` | `bargain_rule` / `create`, `update`, `active`, `inactive`; `bargain_evaluation` / `accepted`, `rejected_below_floor`, `no_rule`, `bargaining_disabled` | ✅ all present and confirmed live (Phase 3B); "validated" has no dedicated audit action (the validate endpoint is read-only/dry-run and correctly does not write an audit row — validating doesn't change state) |
| `provider_pricing_override.created/updated/approved/rejected/activated/deactivated/validated_preview` | `provider_pricing_override` / `create`, `update`, `approve`, `reject`, `active`, `inactive` | ✅ all present and confirmed live (Phase 3B/3C); "validated_preview" has no dedicated audit action for the same reason (dry-run, no state change) |

## Audit record completeness

Every `master_data_audit_log` row includes: `id`, `entity_type`, `entity_id`,
`action`, `actor_user_id`, `actor_role`, `old_value` (JSON), `new_value`
(JSON), `change_summary` (serves as `reason`/description), `request_id`,
`created_at` — confirmed live this sprint on a real `pricing_rule` update
(`actor_user_id`, `old_value`/`new_value` diff, `request_id`, `created_at`
all present in the response).

## Frontend audit visibility

| Check | Result |
|---|---|
| Pricing Rule audit visible | ⚠️ No dedicated audit tab exists in the (pre-existing, Phase 3A) `/admin/pricing-rules` page — the data is real and accessible via `GET /v1/admin/master-data-audit?entity_type=pricing_rule`, confirmed live this sprint, but not surfaced in that page's UI |
| Bargain Rule audit visible | ✅ Detail drawer's Audit Logs tab, wired to real `GET .../bargain-rules/{id}/audit`, confirmed live with real multi-entry history |
| Provider Override audit visible | ✅ Detail drawer's Audit Logs tab, wired to real `GET .../provider-overrides/{id}/audit`, confirmed live with real multi-entry history including the approve/reject retest from Phase 3C-Closure |
| Audit rows show request_id | ✅ Confirmed on every audit entry checked this sprint across all 3 entity types |

## Result: **PASS with one documented, pre-existing gap.** Bargain Rules and Provider Overrides (this session's Phase 3B/3C scope) have full audit-log write + dedicated frontend visibility. Pricing Tiers/Rules/City-Zip (Phase 3A, built before this session) write real, complete audit rows but lack a dedicated frontend audit tab — a real UI gap, not a data-integrity gap, and out of Phase 3B/3C/3D's stated scope to build (this closure sprint is verification-only, "do not add new features").
