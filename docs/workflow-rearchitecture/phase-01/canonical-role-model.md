# Canonical Role Model

Source of truth: `app/core/permissions.py::ROLE_PERMISSIONS` (enforced) and `app/engines/auth/constants.py::ROLES` (mirror vocabulary). Verification: SOURCE_VERIFIED unless noted.

## Roles actually enforced today (10)

### super_admin
- **Scope:** Platform-wide, no tenant_id.
- **Responsibilities:** Full platform control — tenant lifecycle, catalog, pricing, finance, security, roles.
- **Modules accessible:** All `/v1/admin/*` routers (~29 admin_router.py files gate on `require_super_admin`).
- **Approval authority:** Everything — tenant onboarding, verification, package assignment, complaint/dispute resolution.
- **Existing nav:** Super-admin console, all 9 nav groups.
- **Problem:** `require_super_admin` is a strict `role == "super_admin"` check that does **not** recognize the 4 newer admin_* roles below, so those roles are locked out of most admin surfaces despite being designed to replace broad super_admin access (SOURCE_VERIFIED, `app/dependencies/auth.py`).
- **Recommended home:** Home (system health + My Work queue), recommended My Work: onboarding approvals, SLA breaches, security alerts, finance risk items.

### admin_operations / admin_finance / admin_security / admin_readonly
- **Scope:** Platform-wide, least-privilege admin roles gated via `require_permission`/`P.*` constants, intended to replace super_admin for day-to-day admin work.
- **Status:** Only partially wired — most `admin_router.py` files still gate on `require_super_admin` only, so these 4 roles can reach a minority of admin endpoints (e.g. `roles_permissions/admin_router.py` reads only; role CRUD mutation is explicitly noted in code as "no real mutation capability yet for ANY role").
- **admin_readonly** additionally cannot mutate platform users (`require_platform_mutate` blocks it explicitly).
- **Recommended simplified nav:** Same shell as super_admin but with modules hidden if the role's permission set doesn't cover them (progressive disclosure, not a separate app).
- **Verification:** SOURCE_VERIFIED (architectural gap, not yet a workflow-breaking bug since these roles are lightly used).

### tenant_owner
- **Scope:** Single tenant (tenant_id from JWT, enforced by `TenantScopeService`).
- **User-facing name:** Business Owner / Provider Owner.
- **Responsibilities:** Business profile, service catalog & pricing setup, team management, finance/credits, customer engagement, reviews/complaints response.
- **Modules:** `frontend/tenant-portal` `(tenant)` route group — Setup, Team, Operations, Finance, Engagement, Insights groups (8 nav groups, ~84 pages).
- **Restricted actions:** Cannot bypass `access_scope=customer_support_limited` read-only carve-out if set (support-agent-as-tenant_owner masquerade case) — but this carve-out is only enforced on endpoints explicitly wrapped with `require_tenant_mutation_permission`, not universally.
- **Recommended home:** Home + onboarding checklist (already exists, `ONBOARDING_CHECKLIST_ITEMS` in `TenantLayout.tsx`) + My Work.

### staff (Business Manager / Office Staff)
- **Scope:** Tenant-scoped, `StaffScopeService.STAFF_ROLES`.
- **Responsibilities:** Day-to-day operations delegated by tenant_owner — jobs, quotes, staff assignment, customer chat.
- **Modules:** Same tenant-portal shell as tenant_owner, permission-gated subset; also accesses `/staff/*` self-service shell (StaffLayout) for their own profile/jobs.
- **Existing workflow problem:** `staff` and `technician` share most dependency-level access (`require_staff_or_above` includes both) — the UI does not clearly separate "office staff coordinating work" from "technician doing fieldwork"; both currently land on the same `/staff/*` self-service shell.

### technician (Field Technician)
- **Scope:** Tenant-scoped, self-scoped further to `assigned_staff_id == actor.user_id` for job visibility (`StaffScopeService`).
- **Responsibilities:** Accept/execute assigned jobs — on-the-way, inspection, quote flag, work, completion.
- **Modules today:** Two separate frontends — `frontend/tenant-portal/app/staff/*` (web, fuller feature set: skills, service-areas, availability, documents, sessions) and `mobile/staff-app` (narrower: jobs/chat/earnings/profile/notifications only — confirmed feature-parity gap, RUNTIME_VERIFIED via code comment "were never fetched or shown on mobile").
- **Recommended home:** Today (mobile) / Dashboard (web) + My Jobs as the primary queue.

### customer
- **Scope:** Self-scoped, `CustomerScopeService` enforces `customer_id == actor.user_id`, rejects body override.
- **Responsibilities:** Book services, track jobs, approve quotes, pay invoices, manage credits, review, chat, raise complaints, privacy requests.
- **Modules:** `mobile/customer-app` (~26 current screens) plus a nested legacy 19-screen stack still reachable (documented as intentional, not orphaned) — real duplication to flag for consolidation, not a workflow decision to make now.

### guest
- **Scope:** Unauthenticated.
- **Responsibilities:** Public registration/signup, public catalog browsing, public review reading.
- **Modules:** `app/engines/public_registration/router.py`, `package_commerce/public_router.py`, `customer_reviews/public_router.py`, `trust_quality/public_router.py`.

## Roles referenced but NOT implemented (UNVERIFIED as real roles)

`app/engines/roles_permissions/service.py::REQUIRED_ROLE_ORDER` lists 6 additional labels surfaced to the admin Roles UI with `is_implemented: false`: **platform_admin, finance_admin, operations_admin, support_admin, compliance_officer, tenant_manager**. These do not exist in `ROLE_PERMISSIONS` and grant no access. Treat as aspirational placeholders in the UI, not real roles, until backend work implements them (SOURCE_VERIFIED, code docstring calls out the mismatch itself).

## Scope enforcement summary

| Concept | Service | Enforcement |
|---|---|---|
| Tenant boundary | `app/core/tenant_scope.py` | `WHERE tenant_id = actor.tenant_id`; super_admin exempt; rejects tenant_id override in request body |
| Staff/technician boundary | `app/core/staff_scope.py` | Filters to `assigned_staff_id` for staff/technician; tenant_owner/super_admin see full tenant |
| Customer boundary | `app/core/customer_scope.py` | `customer_id == actor.user_id`, rejects override |
| Platform vs tenant | `PLATFORM_STAFF_ROLES` constant | 5 roles with no tenant_id of their own |
| Read-only tenant carve-out | `access_scope=customer_support_limited` | Only enforced where `require_tenant_mutation_permission` is explicitly used — not automatic on every tenant mutation route (gap, needs endpoint audit) |

See `role-navigation-matrix.csv` for the full per-role navigation mapping.
