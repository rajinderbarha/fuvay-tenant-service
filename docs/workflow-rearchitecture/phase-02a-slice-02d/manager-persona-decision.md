# Manager Responsibility Decision

## Decision: REPRESENT_AS_STAFF_PERMISSIONS — architecturally correct target, currently BLOCKED

## Why this decision, not the alternatives
- **Not `REPRESENT_AS_STAFF_TEMPLATE`**: no permission-template mechanism exists anywhere in this codebase (searched; only the flat per-role `ROLE_PERMISSIONS` dict and the unwired per-user `StaffPermission` override table exist — no intermediate "template" concept).
- **Not `TENANT_OWNER_ONLY_RESPONSIBILITY`**: this would mean every operational responsibility (assigning technicians, reviewing quotes, responding to complaints) requires the tenant_owner personally — evidenced against by the fact that `ROLE_PERMISSIONS["staff"]` already exists as a distinct, populated bundle, clearly intended to support delegation, just not yet the *manager-shaped* delegation this brief asks about.
- **Not `NEW_ROLE_ARCHITECTURE_REQUIRED`**: the schema for exactly this need (`StaffPermission`, tenant-scoped, per-user, supports grant and denial) already exists. Building a new role would duplicate a mechanism that's already 90% built.
- **Not `PRODUCT_DECISION_REQUIRED`**: the in-code comment on `ROLE_PERMISSIONS["staff"]` itself says "Can be extended per staff member via StaffPermission table" — the product intent is not ambiguous, it just was never finished.

## Manager responsibilities evaluated against the base `staff` bundle

| Responsibility | In base `staff` bundle today? | Notes |
|---|---|---|
| View assigned and team jobs | Partial — `FIELD_OPS_JOBS_READ` is scoped to "own assigned jobs only" (service enforces) | Team-wide visibility would need an override or a distinct permission |
| Assign technicians | No | Not in base bundle |
| Review inspections | Partial — via own jobs only | |
| Review quotes | Yes — `FIELD_OPS_QUOTES_MANAGE`, scoped to own jobs | Team-wide quote review would need override |
| Manage availability | No | |
| View customers | No — only own-chat visibility (`CHAT_READ`) | |
| Respond to complaints | No | |
| View business details | Partial — `SETTINGS_READ` | |
| Manage staff, where delegated | No | |
| View finance, where delegated | No | |
| Modify finance, where delegated | No | |
| Modify business settings, where delegated | No | |

Most manager-shaped responsibilities require capability beyond the base `staff` bundle — exactly the gap `StaffPermission` overrides were designed to close, and exactly the gap that's unwired.

## What "safe" would require before this decision could move from BLOCKED to implemented
1. `get_current_user` (or the JWT-issuance code path at login) must actually populate real `StaffPermission` grants into the authorization decision — via either a per-request DB lookup (adds latency to every request) or baking overrides into the JWT at issue time (consistent with how `access_scope`/`role` already work, but requires a token refresh or re-login to take effect after any override change — same caveat already documented for role changes in Slice 2C's `token-session-impact.md`).
2. Once wired, a specific manager permission set must be defined (the responsibilities table above is a starting point, not a final specification).
3. Only then would granting `manager@demo-ac-services.local` (or any future manager persona) actual elevated permissions be safe and effective — today it would either silently do nothing (if granted via the dead `StaffPermission` path) or require inventing an unapproved alias role (explicitly forbidden).

## Application to manager@demo-ac-services.local specifically
Even after the wiring gap is closed, this specific account still has zero evidence of *which* permissions it should receive — see `affected-account-final-disposition.md`. The wiring gap and this account's evidence gap are two independent blockers; closing one does not resolve the other.
