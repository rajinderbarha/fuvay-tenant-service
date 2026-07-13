# ServiceOS Canonical Role & Authorization Model (MODULE-L5-01D decision)

**Status:** Authoritative. Resolves `BLK-01D-1`.
**Decided by:** MODULE-L5-01D (Principal Identity Architect role), decision delegated by the
product owner ("you decide").

## 1. The decision (BLK-01D-1)

The MODULE-L5 template mandated a generic 10-role set (`super_admin, platform_admin,
support_admin, tenant_admin, tenant_owner, manager, staff, technician, customer, guest`).
ServiceOS instead has a deliberate, audited **least-privilege** role model. **Option A is
adopted: the product's real model is ratified as canonical.** The generic template names
`platform_admin`, `support_admin`, `tenant_admin`, and `manager` are **not** introduced.

**Why:**
- The four `admin_*` platform roles are a *more secure*, more-granular realization of "platform
  admin" — each carries an explicit, non-overlapping, commented permission set with recorded
  deny rationale (`app/core/permissions.py` lines 633-744), built across FINAL-L5-05L…05U.
  Collapsing them into a single generic `platform_admin` would be a privilege-escalation
  **regression**.
- `tenant_admin` and `manager` have **no** product-defined authority anywhere in the
  repository. Inventing privileged roles from nothing is "unsafe to infer."
- Adopting the product's real model requires **no risky live role-string migration** — the
  enforced registry already *is* canonical.

## 2. The canonical role set (the ONLY active system roles)

Single source of truth: `app/core/permissions.py::ROLE_PERMISSIONS`.

| Role | Scope | Purpose |
|---|---|---|
| `super_admin` | platform | Sole `P.ALL` wildcard; highest platform authority |
| `admin_operations` | platform | Least-privilege: ops jobs, tenant onboarding verify, review moderation, ops dashboards. **No** finance/security. |
| `admin_finance` | platform | Least-privilege: `FINANCE_*`, deposits, top-ups. **Denied** jobs/security/roles. |
| `admin_security` | platform | Least-privilege: `SECURITY_*`, session revoke, IP blocklist, API keys, audit. |
| `admin_readonly` | platform | Read-only across ops/finance/security/tenant. |
| `tenant_owner` | tenant | Tenant's top business authority |
| `staff` | tenant | Tenant operational (enforced; real rows use `technician`) |
| `technician` | tenant | Assignment-scoped tenant operational (actually seeded on staff users) |
| `customer` | self/marketplace | Self-service / booking |
| `guest` | public | Unauthenticated / minimal public catalog read |

The generic `platform_admin` maps to **the union intent of** the four `admin_*` roles but is
deliberately kept split for least-privilege; `support_admin` intent is served by
`admin_security` (bounded read/session) + `admin_readonly`; bounded support troubleshooting also
uses the audited **impersonation** path (`P.PLATFORM_IMPERSONATE`, super-admin-gated).

## 3. Registry consolidation (done this sprint)

- `app/core/permissions.py::ROLE_PERMISSIONS` — **the** enforced registry (unchanged; already
  canonical).
- `app/engines/auth/constants.py::ROLES` — **reconciled** from a stale 5-name list to the
  canonical 10 (was a competing vocabulary; now a kept-in-sync mirror). `AUDIENCE` extended so
  `technician` + the four `admin_*` roles carry correct token audiences instead of falling back
  to `serviceos:customer`.
- `app/engines/roles_permissions/service.py` — read-only **display catalog** (enforces nothing;
  already marks non-existent template roles `is_implemented=false`). No change required; the
  guard confirms it enforces no non-canonical role.

Enforced by `e2e/canonical_role_registry_guard.py` (fail-closed) + controlled-failure tests in
`tests/test_module_l5_01d_canonical_roles.py`.

## 4. Custom roles — decision (Section 18, Option B: formally excluded)

ServiceOS RBAC is code-defined (`ROLE_PERMISSIONS` + `class P`), with per-user overrides via
`StaffPermission` (`staff_permissions` table). There is **no** tenant custom-role subsystem and
no product evidence one is required. Custom roles are **formally excluded** as a current
canonical feature; the extension point (per-user `StaffPermission` overrides) remains for
future need. Custom-role layers are therefore `NOT_APPLICABLE`, not `NOT_IMPLEMENTED`.

## 5. ABAC — decision (Section 19, Option B: RBAC + domain-policy is canonical)

There is **no** user-configurable ABAC policy engine. Attribute-based rules (ownership, tenant
scope, membership/account state, assignment scope, resource state) are enforced as **code-level
domain policies** inside services and the `require_*` dependencies. This RBAC + domain-policy
model is ratified as canonical; full ABAC is `NOT_APPLICABLE` with a clean future extension
boundary.

## 6. Tenant membership — OPEN (BLK-01D-2, product-requirement gated)

ServiceOS models tenancy as a single `User.tenant_id`. There is no multi-tenant membership
table, no tenant switching, and **no repository artifact anywhere** suggesting a single human
must hold memberships in multiple tenants simultaneously (the domain is one provider business
per tenant). Whether multi-tenant-per-user membership is a genuine ServiceOS product
requirement — versus a MODULE-L5 template assumption — is a **product-owner decision** and is
recorded as `BLK-01D-2`. Until answered, single-`tenant_id` (validated) remains canonical; no
membership schema was built, because building an unenforced membership table toward an
unconfirmed requirement is the exact "table without consumers" anti-pattern the mission warns
against.
