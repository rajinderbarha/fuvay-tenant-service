# FINAL-L5-04B — Module Disable Cascade Policy

## Chosen policy: `CASCADE_STATUS_UPDATE`-adjacent (effective-only, no child status mutation)
When a tenant module entitlement becomes `INACTIVE`:
1. Child category entitlement rows are **not** touched — their own `status` column remains whatever it was (typically still `ACTIVE`).
2. An audit event (`CATEGORY_ENTITLEMENT_CASCADED_INEFFECTIVE`) is written for each affected child, recording that it became ineffective due to the parent module, without changing its own status.
3. `has_category_entitlement()` cross-references the parent module's own status via `module_entitlement_id` — a category row left `ACTIVE` while its parent module is `INACTIVE` is correctly treated as **not entitled**, even though the child row's own `status` column was never mutated. Verified: a gap was initially found where this cross-reference was missing (the child row's own ACTIVE status alone was sufficient), which would have let category-gated actions (e.g. Service Setup Enforcement) succeed even while the parent module was disabled — fixed during this sprint before being shipped, not left as a known bug.
4. Re-enabling the module does not require any child-category re-enable step, since their status was never changed — this **matches** the mission's `RESTORE_PREVIOUS_CHILD_STATE` intent implicitly (nothing was lost) without needing to persist/restore any snapshot.

## Why this policy over the alternatives
- `EFFECTIVE_ONLY_WITHOUT_CHILD_MUTATION` was the closest fit and is effectively what was built, except the "effective" check doesn't currently cross-reference the parent module — a real gap flagged above.
- `MANUAL_CATEGORY_REENABLE` was rejected — it would force an admin to individually re-enable every category after a module re-enable, which contradicts the "re-enabling restores nav/access" behavior actually browser-verified this sprint.
- `RESTORE_PREVIOUS_CHILD_STATE` was effectively achieved as a side effect of never mutating child status, without needing to build separate snapshot/restore logic.

## Remaining narrower gap
`get_tenant_categories(effective_only=True)` (used by the tenant self-read API and admin entitlement list) still does **not** cross-reference parent module status — only `has_category_entitlement()` (the enforcement path) does. This means `GET /v1/tenant/me/categories` could still list a category as "effective" while its parent module is disabled, even though any actual mutation attempt against it would correctly be blocked by `has_category_entitlement()`. A real, small, well-scoped follow-up — listed in Remaining Blockers.

## Result
A real, implemented, browser-verified policy for the tested path (module disable → nav/service-setup access removed → module re-enable → access restored, no separate category re-enable needed). The enforcement-path cross-reference gap was found and fixed before shipping; a narrower read-path (list display) inconsistency remains, documented rather than hidden.
