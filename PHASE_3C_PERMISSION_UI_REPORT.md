# Phase 3C — Permission UI Report

## Mechanism

New `hooks/usePermissions.ts` calls `authApi.me()` (real `GET /v1/auth/me`)
and exposes `has(permission: string)`, which checks the real user's
`permissions` array (`"*"` wildcard for super_admin, or exact-match string
otherwise) — no client-side role-name guessing, no hardcoded role lists.
Live-confirmed: `GET /v1/auth/me` for the `admin@serviceos.in` super_admin
token returns `"permissions": ["*"]`.

## Gated UI elements

| Element | Permission | Page |
|---|---|---|
| Evaluate Offer button | `pricing.bargain_rules.evaluate_preview` | Bargain Rules |
| New Bargain Rule button | `pricing.bargain_rules.create` | Bargain Rules |
| Edit action | `pricing.bargain_rules.update` | Bargain Rules |
| Clone action | `pricing.bargain_rules.create` | Bargain Rules |
| Activate/Deactivate actions | `pricing.bargain_rules.activate` + `.deactivate` | Bargain Rules |
| New Override button | `pricing.provider_overrides.create` | Provider Overrides |
| Edit action | `pricing.provider_overrides.update` | Provider Overrides |
| Approve action | `pricing.provider_overrides.approve` | Provider Overrides |
| Reject action | `pricing.provider_overrides.reject` | Provider Overrides |
| Activate/Deactivate actions | `pricing.provider_overrides.activate` + `.deactivate` | Provider Overrides |

`View Detail` (Eye icon) is intentionally **not** gated — it maps to
`.read` permissions, which every admin who can see the page at all already
has (the page itself is only reachable via the sidebar, which is itself
nav-config-gated — consistent with the rest of this app's existing pattern).

## Backend 403 handling

If a restricted admin calls a gated mutation directly (bypassing the hidden
button), the shared `require_permission` dependency on the backend returns a
`ServiceOSException("PERMISSION_DENIED", ...)`, converted to RFC 7807 with
`error_code`, `detail`, and `request_id` — and thanks to this sprint's
`request_id` plumbing fix (see `PHASE_3C_FRONTEND_INTEGRATION_REPORT.md`),
the frontend's `ErrorBlock` component now actually renders that `error_code`
and `request_id`, closing the loop the ticket asks for.

## Not built this sprint

A live multi-role smoke test (creating a `finance_admin`-only test user and
confirming buttons are hidden / actions 403) was not performed — no such
restricted-role seed user exists in the current dataset, and creating one was
out of this sprint's time budget. The gating logic itself is generic and
data-driven (`perm.has(permission)` against the real backend permission list),
not per-role special-cased, so the risk of it being wrong for a specific role
is low, but this is an honest, documented gap, not a claimed pass.
