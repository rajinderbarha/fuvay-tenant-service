# Admin Tenant Detail — Permission Report

## Admin Actions and Required Permissions

All mutations on the Provider 360 page are gated at the backend by `require_admin_user`.
The admin portal JWT does not carry granular permission tokens; all authenticated admin
users receive the same access level.

| Action | Button | Backend Guard | Frontend Guard |
|--------|--------|--------------|---------------|
| Add Usage Credits | Hero + More menu | `require_admin_user` | Always shown to admins |
| Suspend Tenant | Hero (when active) | `require_admin_user` | Shown when `status === "active"` |
| Reinstate Tenant | Hero (when suspended) | `require_admin_user` | Shown when `status === "suspended"` |
| Change Plan | Hero | `require_admin_user` | Always shown to admins |
| Approve / Review Tenant | More menu | `require_admin_user` | Always shown to admins |
| Adjust Security Deposit | More menu | `require_admin_user` | Always shown to admins |
| Request Changes | More menu | `require_admin_user` | Always shown to admins |
| Send Notification | More menu | `require_admin_user` | Always shown to admins |
| Export Report | More menu | `require_admin_user` | Always shown to admins |

## Self-Approval / Self-Mutation Guards

The following business rules are enforced by the backend:

- **Tenant cannot self-approve**: Approval endpoint requires admin JWT — tenant JWT is rejected.
- **Tenant cannot self-verify**: Verification status is set only by admin endpoints.
- **Tenant cannot self-change role/status**: All `suspend`, `reactivate`, `change-plan` actions
  require `require_admin_user` — no tenant-scoped route exposes these.
- **Add Usage Credits requires reason**: Backend validates `reason` is present (non-empty string).

## P1 Gap — Granular Permission Scoping

The spec called for `admin.tenants.credits.add`, `admin.tenants.suspend` etc. permission
checks. These are not available in the current JWT payload. All admin users with a valid
admin JWT have the same access level.

**Mitigation:** Backend enforcement is the authoritative guard. UI currently shows all
action buttons to all admin users — no hidden state, no false security.

**Future work:** When a role/permission system is added to the JWT, wrap each `<button>`
in a `hasPermission("admin.tenants.credits.add")` check.

## Read-Only Access

All data on the Overview, Setup, Operations, Finance, Trust & Quality, Media, and Audit
tabs is read-only for display. No data is modified on tab render. All tab data comes from
existing read endpoints that are also guarded by `require_admin_user`.
