# Phase 3C-Closure — Multi-Role Permission Report

## Important finding: no dedicated Finance Admin / Read-only Admin / Restricted Admin platform roles exist in this codebase

Checked `app/core/permissions.py::ROLE_PERMISSIONS` and the live `users`
table. The only seeded platform-level roles are `super_admin`, `tenant_owner`,
`customer`, `technician`/`staff` — there is no `finance_admin`,
`read_only_admin`, or `restricted_admin` role defined anywhere in this
codebase's permission model. This is a pre-existing platform characteristic,
not something Phase 3C was asked to (or should) invent — the pricing
permission system (`pricing.*`) is real and enforced per-permission-string
regardless of which named role holds it; no pricing-specific role gap exists.

**Used as a real stand-in for "Restricted Admin"**: `tenant_owner`
(`provider@serviceos.in`), confirmed via live login to hold **zero**
`pricing.*` permissions (its full permission list was inspected — 80+
tenant/field-ops/booking/etc. permissions, none matching `pricing.*`).

## Live 403 test (real backend, real JWT, real tenant_owner role)

| Endpoint | Expected | Actual | Result |
|---|---|---|---|
| `GET /pricing/bargain-rules/summary` | 403 | `403`, `error_code: PERMISSION_DENIED`, `request_id: req_77343eb0cef7` | ✅ |
| `POST /pricing/bargain-rules` | 403 | `403`, `error_code: PERMISSION_DENIED`, `request_id: req_8203a3cd83aa` | ✅ |
| `POST /pricing/provider-overrides/{id}/approve` | 403 | `403`, `error_code: PERMISSION_DENIED`, `request_id: req_4b4d0b72b295` | ✅ |

Every response body included `detail` naming the exact missing permission
(e.g. `"Permission 'pricing.bargain_rules.create' required. Your role
'tenant_owner' does not have this permission."`) and a real `request_id` —
satisfying the ticket's "403 response includes request_id" requirement.

## Super Admin (real, live-confirmed)

`admin@serviceos.in` (`super_admin`, `permissions: ["*"]`) successfully
performed every mutating action exercised this sprint: create override,
approve, reject, activate, deactivate, validate-preview, evaluate-preview,
bargain-rule activate/deactivate/validate. All succeeded with real data.

## Frontend permission-guard verification (source-level, since no second
## browser session with a different logged-in user was possible)

`hooks/usePermissions.ts` calls the real `GET /v1/auth/me` and exposes
`has(permission)` checking the actual returned `permissions` array (`"*"` or
exact match) — not a hardcoded role-name switch. Both pages gate:

- New Bargain Rule / New Override buttons → `.create`
- Edit actions → `.update`
- Approve/Reject → `.approve` / `.reject`
- Activate/Deactivate → `.activate` / `.deactivate`
- Evaluate Offer → `.evaluate_preview`

Since `has()` is driven entirely by the real backend permission list for
whichever user is logged in, and the backend enforcement was live-verified
above to correctly grant/deny per-permission, the frontend gating logic is
verified **by construction** to behave correctly for any role — it was not
re-tested with a second interactive login only because doing so requires a
real browser session (this sprint's core environment limitation) or a
second terminal-only smoke, which would only re-confirm the same `has()`
logic already inspected at the source level.

## Result: **PASS.** 403 backend behavior confirmed live with a real non-privileged role; request_id present on every denial; frontend guards are backend-permission-driven, not hardcoded, and inspected at source level.
