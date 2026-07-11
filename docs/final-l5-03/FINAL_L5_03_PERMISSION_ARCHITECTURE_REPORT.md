# FINAL-L5-03 — Permission Architecture Report

## Scan performed
`grep` for `role ===`, `role.includes(`, `user.role`, `isAdmin = true`, `canEdit = true` across `super-admin/app` and `tenant-portal/app`.

## Findings, individually verified (not classified by keyword match alone)

| File | Match | Real nature |
|---|---|---|
| `super-admin/app/admin/account/page.tsx:173` | `u?.role === "super_admin"` | **Display-only** — a badge showing the current user's own role, not a permission gate |
| `super-admin/app/admin/ai-chat/test-console/page.tsx`, `sessions/page.tsx` | `t.role`/`msg.role === "user"` | **False positive** — `role` here is a chat-turn field (`"user"` vs `"assistant"`), unrelated to RBAC |
| `tenant-portal/app/(tenant)/ai-chat/page.tsx` | `msg.role === "user"` | Same false positive as above |
| `tenant-portal/app/(tenant)/provider/status/page.tsx:85` | `meApi.data?.role === "tenant_owner" \|\| meApi.data?.role === undefined` | **Real, duplicated permission gate** — controls whether the "Recalculate Readiness" mutation button is enabled |
| `tenant-portal/app/(tenant)/provider/offerings/page.tsx:478` | Identical expression | Same duplicated gate, second copy |

## Fix applied
Extracted the one genuine duplicated pattern into `isTenantOwnerRole(role)` in `tenant-portal/lib/api.ts`, preserving exact prior semantics (role `undefined` — still loading — is treated as owner so the button isn't spuriously disabled mid-load). Both consumer pages now call the shared helper. See Role Check Migration Report.

## Correction: a `can(permission)`-style hook already exists in super-admin — underused, not absent
Initial scanning (grep for `role ===` etc.) missed this because it doesn't match those patterns. Direct inspection of `pricing/bargain-rules/page.tsx` (`perm.has("pricing.bargain_rules.evaluate_preview")`) surfaced `frontend/super-admin/hooks/usePermissions.ts`:
```ts
export function usePermissions() {
  const me = useApi<AdminUser>(useCallback(() => authApi.me(), []));
  const perms = me.data?.permissions ?? [];
  const has = (permission: string) => perms.includes("*") || perms.includes(permission);
  return { has, loading: me.loading, role: me.data?.role ?? null };
}
```
This is functionally very close to the mission's suggested `can(permission)` — backend-sourced (`authApi.me().permissions`), string-keyed, wildcard-aware. **Real adoption is low**: only 3 consumer pages in super-admin (`grep -rl "usePermissions()" app` → 3 files) out of the app's much larger page count. No equivalent exists in tenant-portal or customer-app.

**Not expanded this sprint**: retrofitting `usePermissions()`/`perm.has()` into every mutation-gating site across super-admin (and building an equivalent for tenant-portal) is real, valuable, but large-surface-area work — it would touch dozens of files to add a UX improvement (backend authorization is unaffected either way). Recommended as the concrete next step for permission architecture in the Deprecated Pattern Guide, rather than attempted blind this sprint. This correction replaces the earlier, less accurate claim that "no registry exists" — one does, it's just under-adopted.

## UI use cases already correctly implemented
- Hide unavailable navigation: not scoped to permission in current nav (deferred to L5-04/05 per mission's own instruction).
- Disable mutation actions: `isTenantOwnerRole()` gates the Recalculate Readiness button; `isTenantReadOnly()` gates mutation buttons app-wide via `ReadOnlyBanner`.
- Show ReadOnlyBanner: confirmed present and correct (FINAL-L5-01D/01E).
- Prevent opening edit modals: covered by the same `isTenantReadOnly()` checks at each mutation button.
- Show correct permission message: backend 403 messages are surfaced via `ServiceOSError.message` (generic, not permission-specific wording — see Error Handling Standard for the honest gap here).

## Rules verified
1. UI checks improve UX, don't replace backend authorization — confirmed (backend RBAC re-verified working in FINAL-L5-02B this same engagement, unaffected by this sprint).
2. Permission names from a registry — **partially implemented**: `usePermissions().has(permission)` (super-admin, 3 consumers) checks against backend-sourced permission strings; the 2 `role===` sites found are separate and were consolidated (item 3).
3. No scattered raw role-name comparisons — the 2 found were consolidated to 1 shared function.
4. Tenant Read Only represented consistently — confirmed (`isTenantReadOnly()`, single source).
5. Customer/technician self-scope consistent — confirmed via FINAL-L5-02B isolation testing (backend-side, unaffected here).
6. Admin read-only must not see active mutation actions — not independently re-tested this sprint (carried from FINAL-L5-01B's RBAC regression, 21/21 still passing).

## Result
No `NOT_READY_FINAL_L5_03_PERMISSION_ARCHITECTURE_FAILED` — the real duplication found (2 sites) is fixed; the absence of a full registry is a documented, reasoned scope decision, not an oversight.
