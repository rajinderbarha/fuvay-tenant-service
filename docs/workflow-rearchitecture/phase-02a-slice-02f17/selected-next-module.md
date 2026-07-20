# Selected Next Module — `app.engines.platform_notifications.provider_router`

## Selected module
`app.engines.platform_notifications` — specifically the provider- and staff-facing chat and notification routers defined in `app/engines/platform_notifications/provider_router.py`:
- `provider_notif_router` (prefix `/v1/provider/notifications`)
- `provider_chat_router` (prefix `/v1/provider/chat`)
- `provider_audit_router` (prefix `/v1/provider/audit-logs`) — read-only, not part of the 10 mutation routes, but part of the same coherent module boundary
- `staff_notif_router` (prefix `/v1/staff/notifications`)
- `staff_chat_router` (prefix `/v1/staff/chat`)

## Mounted prefixes
`/v1/provider/notifications`, `/v1/provider/chat`, `/v1/provider/audit-logs`, `/v1/staff/notifications`, `/v1/staff/chat`.

## Exact route count
10 mutation-method routes (all currently `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK`) — see `selected-next-module-route-list.csv` for the complete list.

## Parent models
`ChatThread`, `ChatMessage` (`app/engines/platform_notifications/chat_service.py`'s underlying models), `Notification`/notification-preference records (`notification_service.py`), all scoped by `tenant_id` per the module's existing `_tid(u)` helper (confirmed present in the router file — used for READS, not yet enforced as an authorization gate on writes).

## Persona policy (current, to be closed by the selected slice)
All 10 routes currently accept any authenticated user via bare `get_current_user` — no role, permission, or ownership check exists. The intended persona split (inferred from the router's own prefix structure, not yet enforced in code) is:
- `/v1/provider/*` routes → `tenant_owner`/`staff`/`super_admin` acting on their own tenant's chat/notifications.
- `/v1/staff/*` routes → `staff`/`technician`/`tenant_owner`/`super_admin` (the module's own separate `staff_notif_router`/`staff_chat_router`, mounted distinctly from the provider ones, suggesting a deliberate staff-vs-owner split already exists in ROUTING but not in AUTHORIZATION).

## Existing permissions/dependencies available for reuse
`require_owner_or_office_staff_mutation`, `require_staff_or_above_mutation`, `require_tenant_mutation_permission` — all already exist and are used identically elsewhere in this codebase (including the just-closed `quote_checklist` module, an excellent structural precedent: dedicated provider/staff routers in one file, closed with `require_owner_or_office_staff_mutation` after confirming no technician caller evidence).

## Primary gaps
- `AUTHENTICATED_ONLY` (all 10 routes) — the router-level gap.
- `CROSS_TENANT_IDOR` (thread/notification creation and read/mark-read actions have no confirmed tenant or thread-membership ownership check) — the service-layer gap, requiring investigation during implementation (not yet proven, inferred from the established defect pattern seen in every other `AUTHENTICATED_ONLY` module closed by this initiative).

## Alternate routes
`app/engines/platform_notifications/customer_router.py` and `admin_router.py` exist as SEPARATE files for the customer and platform-admin personas respectively — confirmed structurally distinct, not touched by this selection, no same-record bypass expected between them (mirrors the quote_checklist precedent's provider/customer/admin router separation).

## Read surfaces
Not modified by selection (implementation slice's own scope) — `provider_audit_router` and the various GET routes in this file are out of this discovery slice's scope to classify exhaustively; noted as an implementation-time task.

## Financial or lifecycle effects
None identified — chat/notifications are a communication feature with no direct financial or Job/Booking lifecycle side effect.

## Why it outranks the other candidates
1. **Severity**: the ONLY `CRITICAL`-scored remaining module (`module-risk-scoring.csv`) — zero authorization (not merely missing access-scope) across ALL 10 routes, admitting literally any authenticated account of any role or tenant.
2. **Blast radius**: chat threads and notifications are core, always-on business communication surfaces (unlike `analytics.provider_router`'s single low-traffic report-run route, or `admin_catalog`'s narrow setup routes).
3. **Manageable scope**: 10 routes in ONE file, ONE engine, with an already-established structural precedent (`quote_checklist`'s identical provider/staff-router-in-one-file pattern, closed successfully with `require_owner_or_office_staff_mutation` in Slice 2F-16) directly transferable here.
4. **No blocking product decision**: the persona split (owner/staff vs. staff-only) is already structurally expressed in the router's own prefix/file organization — no ambiguous policy question needs resolving first (unlike, say, `compliance.provider_router`'s DPDP export-generation rate-limiting, which may need a product decision about throttling).
5. **No pipeline merge, no new role/permission needed**: closable entirely with dependencies that already exist and are already proven correct in this codebase.

## Why it is safe to implement next
- Read-only routes (list threads, get messages, audit log reads) are unaffected — only the 10 identified WRITE routes need a dependency added.
- The fix pattern (swap `get_current_user` for `require_owner_or_office_staff_mutation`/`require_staff_or_above_mutation`, add object-ownership checks at the service layer) is now well-established and low-risk, having been successfully applied to `quote_checklist` (Slice 2F-16), `booking.router` (2F-15A), and `field_ops.router` (2F-14 series) with zero regressions each time.
- No customer-facing behavior changes (the customer chat/notification router is a separate file, untouched).

## Explicit out-of-scope boundaries for the implementation slice
Per this discovery slice's own OUT-OF-SCOPE list (which the FUTURE implementation slice must also respect unless its own mission explicitly permits otherwise): no new role/permission, no migration, no pipeline merge, no frontend changes, no `My Work`/`Next-Action` work. The implementation slice should also explicitly scope itself to `app/engines/platform_notifications/provider_router.py`'s 10 mutation routes and their directly-connected service-layer ownership checks — not the entire `platform_notifications` engine (customer_router.py, admin_router.py, and the read/GET routes in provider_router.py are separate concerns).
