# FINAL-L5-01B — Rule API Readiness Report

## Method
Given this sprint's live-server verification limitation (documented in the RBAC fix report — the sandboxed tool environment cannot reliably restart/interact with the shared dev server process), API readiness was checked at the data layer (direct DB query confirming records are queryable and well-formed) rather than via live HTTP calls through Admin-authenticated sessions this time.

## Findings

| Domain | Data present | Human-readable name | Active state | Raw blob only? |
|---|---|---|---|---|
| Health Rules | Yes, 4 rows | Yes (`name` field, e.g. "Provider Business Health") | Yes (`status='active'`) | No — structured columns (`base_score`, `min_score`, `max_score`) alongside the name |
| Badge Rules | Yes, 5 rows | Partial — `badge_rules.rule_key` is a slug (`rule_verified_provider`); the human-readable name lives on the joined `badge_definitions.name` table, not on the rule row itself | Yes (`status='active'`) | No, but requires a join to `badge_definitions` for a UI-facing label — noted as a join requirement, not a raw-blob problem |
| Matching Rule | Yes, 1 row | Yes (`name='Provider-First Home Services Matching'`) | Yes (`status='active'`) | No — `condition_json`/`recommendation_json` are structured payloads alongside `name`/`description`, not the only UI-facing content |
| Notification Policy (channel config substitute) | Yes, 4 rows | Partial — no dedicated `name` field on `notification_channel_configs`; the human-readable policy name is embedded inside the `config` JSON payload (`config.policy_name`) rather than a first-class column | Yes (`is_enabled`) | Borderline — the policy name is inside the JSON blob, which is not ideal UI ergonomics but is not the *only* content (channel/enabled state are structured columns) |

## Not verified this sprint
List/Create/Update/Activate/Deactivate/Version-history endpoints for these domains were not individually called via authenticated HTTP this sprint (live-server limitation). Permission enforcement on rule-domain endpoints specifically (as opposed to the tenant-admin router this sprint's RBAC fix targeted) was not audited — a real, undone task, flagged in remaining blockers.

## Assessment
Data exists and is structurally sound for 3 of the 6 real-schema domains (Health, Badge pre-existing; Matching newly seeded). The Notification Policy substitute has a minor ergonomic gap (name embedded in JSON) worth a follow-up schema note but is not a blocker — it is real, queryable, structured data, not a runtime mock fallback.
