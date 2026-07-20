# Affected Account Investigation

Method: read-only SQL queries against the live configured database, same connection used in Slice 2B. No account identifier beyond email/user_id/tenant_id is reproduced here — no phone numbers, password hashes, or session tokens are included anywhere in this document.

## Account 1 — manager@demo-ac-services.local

| Field | Value | Verification |
|---|---|---|
| User ID | 72640932-ef3c-4ce5-92a1-6609bff35ee0 | RUNTIME_VERIFIED |
| Tenant membership / Tenant ID | demo-ac-services / 5209ef33-a53e-4fc0-b3f6-006335b8d712 | RUNTIME_VERIFIED |
| Account status | active, is_verified=true, is_active=true | RUNTIME_VERIFIED |
| Creation timestamp | 2026-07-11 05:02:53 UTC | RUNTIME_VERIFIED |
| Creator / invitation source | `scripts/canonical_seed_final_l5_01.py` (direct ORM insert, bypasses all API validation) — `invited_by_user_id` is NULL, consistent with non-API creation | RUNTIME_VERIFIED (source) + RUNTIME_VERIFIED (invited_by_user_id NULL) |
| Original invitation record | None exists — no invitation-table concept in this schema (confirmed Slice 2B); this row IS the "invitation" (created with `force_password_change`) | SOURCE_VERIFIED |
| Historical role value | Always `tenant_manager` since creation (single seed script write, no update history found) | RUNTIME_VERIFIED |
| Related audit records | **Zero** — no `auth_audit_logs` row of any action_type for this user_id | RUNTIME_VERIFIED |
| Login history | **Never logged in** — `last_login_at IS NULL`, zero rows in `user_sessions` | RUNTIME_VERIFIED |
| Existing staff profile | None — zero rows in `provider_team_members` | RUNTIME_VERIFIED |
| Existing technician profile | None (same table, same check) | RUNTIME_VERIFIED |
| Team membership | None found | RUNTIME_VERIFIED |
| Staff designation | None recorded anywhere | RUNTIME_VERIFIED |
| Permission overrides | Zero `staff_permissions` rows | RUNTIME_VERIFIED (from Slice 2B, re-confirmed) |
| Assigned jobs | Zero `service_jobs` rows with `assigned_staff_id` = this user | RUNTIME_VERIFIED |
| Created records | None found (zero non-login audit actions of any kind) | RUNTIME_VERIFIED |
| Approval activity | None | RUNTIME_VERIFIED |
| Finance activity | None found in the tables checked | SOURCE_INFERRED (not every finance table individually queried) |
| Existing frontend destination | Would land in `TenantLayout` if it could ever log in and if `tenant_manager` were recognized — moot, since it's unrecognized | SOURCE_INFERRED |
| Ever successfully authenticated | **No** | RUNTIME_VERIFIED |
| Currently zero effective permissions | **Yes** — `tenant_manager` is absent from `ROLE_PERMISSIONS` | SOURCE_VERIFIED |
| Evidence of intended responsibility | Only `full_name`="Tenant Manager" and email local-part "manager" — both are name-similarity signals, which the rules explicitly disallow as sufficient basis | SOURCE_VERIFIED |

**Assessment:** an entirely unused demo account. No behavioral evidence exists beyond its name. Per the explicit rule against inferring from name similarity, this account's intended role cannot be established with the evidence available.

## Account 2 — readonly@demo-ac-services.local

| Field | Value | Verification |
|---|---|---|
| User ID | 05deaee8-03f2-40f9-8af6-2f21892c075f | RUNTIME_VERIFIED |
| Tenant membership / Tenant ID | demo-ac-services / 5209ef33-a53e-4fc0-b3f6-006335b8d712 (same tenant as account 1) | RUNTIME_VERIFIED |
| Account status | active, is_verified=true, is_active=true | RUNTIME_VERIFIED |
| Creation timestamp | 2026-07-11 05:02:53 UTC (same batch as account 1) | RUNTIME_VERIFIED |
| Creator / invitation source | Same seed script, same non-API creation path | RUNTIME_VERIFIED |
| Original invitation record | None (same reasoning as account 1) | SOURCE_VERIFIED |
| Historical role value | Always `tenant_readonly` since creation | RUNTIME_VERIFIED |
| Related audit records | **7 rows, all `action_type='login.success'`, all `outcome='success'`, spanning 2026-07-11 05:27 through 2026-07-13 09:08 UTC. Zero rows of any other action_type.** | RUNTIME_VERIFIED |
| Login history | **7 successful logins** | RUNTIME_VERIFIED |
| Existing staff profile | None — zero `provider_team_members` rows | RUNTIME_VERIFIED |
| Existing technician profile | None (same table) | RUNTIME_VERIFIED |
| Team membership | None found | RUNTIME_VERIFIED |
| Staff designation | None recorded | RUNTIME_VERIFIED |
| Permission overrides | Zero `staff_permissions` rows | RUNTIME_VERIFIED |
| Assigned jobs | Zero | RUNTIME_VERIFIED |
| Created records | **None** — despite 7 logins, zero non-login actions were ever recorded; consistent with the account being able to authenticate but unable to perform any action, since its role grants no permissions | RUNTIME_VERIFIED |
| Approval activity | None | RUNTIME_VERIFIED |
| Finance activity | None found in tables checked | SOURCE_INFERRED |
| Existing frontend destination | Whatever `TenantLayout` renders for a role it doesn't recognize — likely a broken/empty experience every one of the 7 times, though the exact frontend behavior for an unrecognized role was not independently re-traced this slice | SOURCE_INFERRED |
| Ever successfully authenticated | **Yes, 7 times** | RUNTIME_VERIFIED |
| Currently zero effective permissions | **Yes** — `tenant_readonly` is absent from `ROLE_PERMISSIONS`, and no canonical role represents "tenant-side read only" at all | SOURCE_VERIFIED (confirmed again this slice, unchanged from Slice 2B) |
| Evidence of intended responsibility | Real usage pattern (7 logins) proves *someone* actively wanted this account to work, but provides zero evidence of *which* canonical role they needed, since every login produced no further recorded action | RUNTIME_VERIFIED (usage) / UNVERIFIED (intended role) |
| Currently has 7 unrevoked sessions | **Yes** — every one of the 7 `user_sessions` rows has `revoked_at IS NULL` | RUNTIME_VERIFIED |

**Assessment:** this account has real, repeated, currently-unrevoked usage — a materially different risk profile from account 1 — but there is genuinely no canonical role to map it to. "Read-only tenant user" does not exist in the 10-role registry. This is not an evidence gap that more investigation could close; it is a real product gap (no canonical role for this designation exists yet).

## Summary
Neither account can be safely, automatically remediated under this slice's evidentiary standard. See `remediation-decision-register.md` for the formal disposition of each.
