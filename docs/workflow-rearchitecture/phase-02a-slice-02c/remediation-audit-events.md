# Remediation Audit Events

## Status: no events created this slice (no remediation was applied)

## Design (built into the script, verified by code, not yet exercised against a real apply)

`scripts/workflow_rearchitecture/remediate_invalid_roles.py`'s apply path writes one row to `auth_audit_logs` (the existing, canonical audit table — confirmed to exist and be used for exactly this purpose by `auth/service.py::change_platform_role`, which this script's audit-write logic mirrors) per changed account:

| Column | Value |
|---|---|
| `id` | freshly generated UUID |
| `actor_id` | NULL (system/script-driven, not an interactively-authenticated admin) |
| `actor_role` | `'system'` |
| `tenant_id` | the affected account's tenant_id |
| `action_type` | `'role.remediation'` |
| `target_id` | the affected user's id |
| `target_type` | `'user'` |
| `outcome` | `'success'` |
| `metadata` | JSON: `{previous_role, new_role, reason, script_version}` |
| `created_at`/`updated_at` | `now()` |

This satisfies the brief's per-change audit requirement (affected user via `target_id`, tenant via `tenant_id`, previous/new role in `metadata`, reason in `metadata`, acting identity via `actor_role='system'` + `script_version`, timestamp via `created_at`) using the **existing** `auth_audit_logs` table and its existing column shape — no new audit table or architecture was created, per the brief's instruction to add "the smallest appropriate event without redesigning audit architecture."

## Not included in the audit row
- Session-revocation result and notification result are **not** currently written into the audit metadata, because (per `token-session-impact.md`) session revocation itself was not implemented in this slice's script (no mapping was ever applied, so this was never exercised). If revocation is added in a future slice, its result should be added to the same `metadata` JSON object (e.g. `sessions_revoked: <count>`) rather than a separate audit row, to keep one audit row per logical change.

## Verification
SOURCE_VERIFIED — the INSERT statement and its column values were read directly from the script (not run against a real target this slice, since no apply occurred). The audit-write code path itself was exercised in earlier slices' patterns (`change_platform_role`'s existing, structurally identical `self._audit(...)` call) — this script's raw-SQL INSERT targets the same table with the same shape, so the mechanism is proven to work in this codebase generally, even though this specific script's INSERT statement was not executed live this slice.
