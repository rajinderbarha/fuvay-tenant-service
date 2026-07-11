# FINAL-L5-01B-PLUS — Formal Classification of the 4 Missing Rule Domains

Per FINAL-L5-01B's rule model inventory, 4 of the mission's 10 rule domains have no dedicated backing table in the current schema (confirmed via exhaustive `information_schema.tables` search). Formal classification below.

| Domain | Classification | Evidence | Rationale |
|---|---|---|---|
| **Reward Rules** | `NOT_SEEDABLE_NO_SCHEMA` | Zero matches for `%reward%` across `information_schema.tables` | No table exists to represent a reward-rule concept at all — not a naming mismatch, a genuine absence. Closest adjacent concept (`badge_rules`) rewards *recognition*, not the mission's described "reward conditions" (implying a customer/provider incentive mechanism) — not a safe substitute. |
| **Credit Threshold Rules** | `NOT_SEEDABLE_NO_SCHEMA` | Zero matches for `%threshold%`, `%credit_alert%`, `%low_credit%` | The "Low Usage Credit Alert" concept from the mission spec has no queryable configuration row anywhere; any threshold logic, if it exists at all, is hardcoded in application code rather than data-driven. Not verified either way this sprint — the absence of a *table* is the confirmed fact; whether a hardcoded threshold constant exists in Python was not searched. |
| **Provider Verification Rules** | `NOT_SEEDABLE_NO_SCHEMA` | Zero matches for `%verification_rule%`, `%provider_verif%` | `tenants.verification_status` is a plain enum column (`pending`/`verified`/etc.) set directly, not driven by a separate configurable "rule" table describing verification *criteria*. The mission's ask (a rule defining verification standards) doesn't exist as data — verification is a state, not a policy. |
| **Notification Policy** | `NOT_SEEDABLE_NO_SCHEMA` (with a partial adjacent substitute) | No standalone "policy" table; `notification_channel_configs` exists (per-tenant channel enable/config, seeded in FINAL-L5-01B) and `notification_templates`/`notif_event_templates` exist (message content) | Closest available real structure is `notification_channel_configs`, which was used as a best-effort substitute in FINAL-L5-01B (4 rows seeded for Demo AC Services, `config.policy_name` field carries the human-readable policy name). This is **not** a true standalone policy record — it conflates channel-enablement with the broader "which events notify which roles" policy concept the mission describes. |

## Why none were fabricated
Per the non-negotiable rule "Do not fabricate configuration records that violate existing schemas" — inventing new tables/columns to satisfy these 4 domains is explicitly out of scope for a data-seeding sprint. Each is a genuine schema-design gap requiring a proper migration + model + service + API design pass, not a seed-script workaround.

## Disposition
All 4 are formally logged as `NOT_SEEDABLE_NO_SCHEMA` and carried to the FINAL-L5-02 remaining-work backlog as schema-design items, distinct from data-seeding items. No further action taken this sprint.
