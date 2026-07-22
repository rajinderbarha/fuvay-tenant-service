# Tenant Access Model

> **CORRECTION (Phase 2A Slice 2E):** the finding below that "zero code anywhere populates `permission_overrides`" was **partially wrong**. Slice 2E found that `app/engines/auth/service.py`'s `_build_token_pair` and the token-refresh path already loaded real `StaffPermission` rows into the JWT's `permission_overrides` claim at login/refresh time — that half of the pipeline was already built. The actual gap was narrower: `app/dependencies/auth.py::get_current_user` never read that claim back out when reconstructing `UserContext`. This was missed in this document's original grep-based search (`permission_overrides\s*=` as a variable assignment) because the JWT-embedding code used dict-literal syntax (`"permission_overrides": staff_perms`), which that pattern didn't match. Slice 2E closed the one-line gap and confirmed the manager-persona backend pipeline (`invite_staff`/`update_permissions`, both pre-existing) now works end-to-end. See `docs/workflow-rearchitecture/phase-02a-slice-02e/effective-permission-architecture.md` for the corrected, complete picture. This document's per-persona conclusions below are superseded for personas B/C where they depended on the override-wiring gap — see Slice 2E's `manager-persona-implementation.md`.

## Architecture findings (Workstream 1)

| Question | Finding | Verification |
|---|---|---|
| Are staff permissions additive? | Yes — `ROLE_PERMISSIONS["staff"]` is a flat list; `PermissionChecker.has()` checks membership, `P.ALL`, then per-user overrides, then engine/resource wildcards | RUNTIME_VERIFIED |
| Can staff permissions remove capabilities? | Yes, in schema — `StaffPermission.is_granted` supports `False` (explicit denial) — but see wiring gap below | SOURCE_VERIFIED (schema) / dead in practice |
| Are permissions role-derived? | Yes, primarily — the flat `ROLE_PERMISSIONS[role]` list is the base | RUNTIME_VERIFIED |
| Do explicit denials exist? | In schema only (`is_granted=False`) — never actually enforced, since overrides are never populated | SOURCE_VERIFIED |
| Do permission overrides exist? | Yes, as a DB table (`staff_permissions`) and a `PermissionChecker.has(overrides=...)` parameter | RUNTIME_VERIFIED |
| **Are overrides ever populated into a real request's authorization decision?** | **No.** `get_current_user` builds `UserContext` entirely from JWT payload fields; none of those fields include per-user overrides, and no other code path sets `UserContext.permission_overrides`. Confirmed by reading `get_current_user`'s full source and grepping all of `app/` for any assignment to this attribute — zero found. | **RUNTIME_VERIFIED — this is the central finding of this slice** |
| Are overrides tenant-scoped? | Yes, in schema (`StaffPermission.tenant_id` is required, non-null) | SOURCE_VERIFIED |
| Are overrides user-scoped? | Yes (`user_id` + `permission_key` unique together) | SOURCE_VERIFIED |
| Are overrides team-scoped? | No team/group-level override concept exists — only per-user | SOURCE_VERIFIED |
| Are manager responsibilities represented through permissions? | No dedicated "manager" permission bundle exists; the base `staff` bundle is scoped to own-job field-technician work only | SOURCE_VERIFIED |
| Do designations affect authorization? | No — `provider_team_members.designation` (a free-text field) is display-only, never checked by any authorization dependency | SOURCE_VERIFIED |
| Can read-only access be represented without a new role? | Partially — `access_scope="customer_support_limited"` + `require_tenant_mutation_permission` is a real, working mechanism, but only wired into 2 of ~16 tenant mutation routers | RUNTIME_VERIFIED |
| Do route dependencies check role, permission, or both? | Both, depending on the route: `require_super_admin`/`require_tenant_owner`/etc. check role only; `require_permission`/`require_any_permission` check the permission bundle; `require_tenant_mutation_permission` checks both permission AND `access_scope` | RUNTIME_VERIFIED |
| Does service-layer authorization match router authorization? | Not comprehensively re-verified this slice beyond the specific paths audited in Slice 2C (`tenant_engine/admin_service.py`, `auth/service.py`) | SOURCE_INFERRED |
| Does frontend navigation use role, permissions, or both? | Both — confirmed in Slice 2 (`usePermissions()` fetches real permissions from `GET /v1/auth/me`; some nav items also check `role === "super_admin"` directly via the `SUPER_ADMIN_ONLY` sentinel) | RUNTIME_VERIFIED (Slice 2 finding, re-confirmed applicable) |
| Do permission changes invalidate sessions or caches? | No cache exists to invalidate (confirmed Slice 2C — no server-side permission cache found); but since role/permissions are baked into the JWT at issue time, a permission change requires session revocation to take effect promptly (Slice 2C finding) | RUNTIME_VERIFIED |

## Persona model

### A. Tenant Owner
- Canonical role: `tenant_owner`
- Required permissions: full `ROLE_PERMISSIONS["tenant_owner"]` bundle
- Forbidden: platform-scoped permissions
- Tenant scope: own tenant, full
- Navigation scope: full tenant-owner shell
- Mutation authority: full within tenant
- Approval authority: full within tenant
- Existing architecture enforces this: **Yes** — RUNTIME_VERIFIED

### B. Tenant Operational Manager
- Canonical role: `staff` (no new role)
- Required permissions: base `staff` bundle **plus** team-wide job visibility, technician assignment, complaint response, customer list, quote/inspection review — **none of which the base `staff` bundle grants today**
- Forbidden: finance mutation, business-settings mutation (unless separately delegated)
- Tenant scope: own tenant
- Navigation scope: would need the same tenant-portal shell, permission-filtered
- Mutation authority: team-job-scoped, not owner-level
- Approval authority: quote/inspection review only
- Existing architecture enforces this: **No — BLOCKED.** The permission bundle this persona needs beyond base `staff` can only be granted via `StaffPermission` overrides, which are never wired into `UserContext`. See `manager-persona-decision.md`.

### C. Tenant Finance-Capable Staff
- Canonical role: `staff`
- Required permissions: base bundle + finance-read/adjust permissions, delegated
- Same blocker as persona B (needs override wiring)
- Existing architecture enforces this: **No — BLOCKED**, same reason

### D. Tenant Support Staff
- Canonical role: `staff`
- Required permissions: base bundle (chat, customer view) — this persona is arguably already close to what base `staff` grants (`CHAT_READ`, `CHAT_WRITE`, `REVIEW_READ`)
- Existing architecture enforces this: **Largely yes**, for the narrow "respond to customer chat" responsibility already in the base bundle; broader support responsibilities (viewing all customers, not just own-chat) would hit the same override-wiring blocker

### E. Tenant Read-Only User
- Canonical role: would need `staff` + a comprehensive mutation-denial guard
- Required permissions: read-only subset of whatever module they need to view
- Forbidden: every mutation permission
- Existing architecture enforces this: **No — BLOCKED.** The one real mechanism (`access_scope` + `require_tenant_mutation_permission`) is only wired into 2 of ~16 tenant mutation routers. See `tenant-readonly-decision.md`.

### F. Technician
- Canonical role: `technician`
- Required permissions: `ROLE_PERMISSIONS["technician"]` (not independently re-read this slice, but its enforcement pattern mirrors `staff`'s, confirmed working in Slices 1-2B for the ServiceJob/Parts workflows)
- Existing architecture enforces this: **Yes** — RUNTIME_VERIFIED (extensively exercised in Slices 1-2B)

## Summary
Personas A, D (narrowly), and F are fully supported by existing architecture. Personas B, C, and E all hit one of two real, evidenced architectural gaps: (1) `StaffPermission` overrides are unwired, or (2) the read-only mutation guard has narrow coverage. Neither gap is a "we don't know what to build" product question — both are "we know what to build, we haven't built the wiring/coverage yet" engineering completion gaps. Closing either is out of this slice's bounded scope (each would require touching the auth dependency chain or 14+ router files respectively) but is now precisely scoped for a future slice.
