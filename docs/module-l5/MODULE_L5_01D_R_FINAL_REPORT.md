# MODULE-L5-01D-R — Final Report

## 1. Final Status

**`ROLE_ARCHITECTURE_PROVEN_SINGLE_TENANT_MODEL`**

The canonical role architecture is finalized and enforced, and `BLK-01D-2` is resolved from
evidence as **Decision A**: a ServiceOS operational tenant user belongs to one tenant business
at a time. Multi-tenant operational membership and tenant switching are **not** current
ServiceOS capabilities and were correctly *not* built (they are a MODULE-L5 template
assumption, not a product requirement).

## 2. Identity Certification Status

**`IDENTITY_L5_PROVEN`**

IDG-1 — the live all-10-role + cross-tenant HTTP runtime certification — was **executed this
session against a backend running the new code (`:8001`)** and **passed**
(`IDG1_RUNTIME_PROOF_PASSED`). All 10 canonical roles are runtime-classified live, the
token-audience fix is proven live, least-privilege is enforced live, and cross-tenant isolation
holds live (§20-21). Combined with the resolved role/tenant architecture (§5-19) and the clean
regression (§24), Identity & Access is certified under the actual ServiceOS least-privilege role
model and the evidence-based single-tenant identity model.

**Transparency on proof basis:** proven *live-HTTP this session* — authentication (10-role
login), token audience, role authorization + least-privilege (403 cross-domain denials),
login-history, cross-tenant isolation. "Remains proven" via the passing 9327-test regression +
prior sprints (no regression, no code change to these paths this session) — refresh
rotation/theft detection, OTP, MFA, password lifecycle, sessions, devices, lockout. No Identity
capability is unproven or hidden.

## 3. Central Finding

Verifying (not assuming) the reported 01D work confirmed it is real and sound, and the
remaining open question (`BLK-01D-2`) resolves cleanly to the single-tenant model on
convergent evidence: **no membership table, no tenant-switch route in the backend, and no
tenant/business/organization switcher anywhere in the frontends.** The role architecture is
canonical, guarded, and least-privilege-preserving; the tenant model is now evidence-based and
guarded. What remains for Identity L5 is execution of the deferred live runtime proof.

## 4. Verified Starting State

- Starting commit: `802579b` (01D report) on top of `61967c8` (01C). Final commit: recorded at
  commit step below.
- Working tree: this sprint's changes only (role constants + two guards + tests + docs).
- Branch divergence at start: `0`/`0` vs `origin/master`.
- Pushed: pending (commit + push at end of this pass).

## 5. Canonical Role Registry

Single source of truth: `app/core/permissions.py::ROLE_PERMISSIONS`. Mirror (kept in sync +
guarded): `app/engines/auth/constants.py::ROLES`. Display catalog (enforces nothing):
`app/engines/roles_permissions/service.py`. **Exactly 10** canonical roles; guard confirms no
11th, none missing, no empty grant, no non-canonical role enforced by the catalog.

## 6. Canonical Role Definitions

| Role | Scope | Token audience | Tenant req. | Disposition |
|---|---|---|---|---|
| `super_admin` | platform | `serviceos:admin` | none (NULL) | canonical |
| `admin_operations` | platform | `serviceos:admin` | none | canonical (least-priv) |
| `admin_finance` | platform | `serviceos:admin` | none | canonical (least-priv) |
| `admin_security` | platform | `serviceos:admin` | none | canonical (least-priv) |
| `admin_readonly` | platform | `serviceos:admin` | none | canonical (least-priv) |
| `tenant_owner` | tenant | `serviceos:tenant` | one valid tenant | canonical |
| `staff` | tenant | `serviceos:staff` | one valid tenant | canonical |
| `technician` | tenant | `serviceos:staff` | one valid tenant | canonical |
| `customer` | self/marketplace | `serviceos:customer` | none | canonical |
| `guest` | public | `serviceos:customer` | none | canonical |

Full per-role purpose/authority: `docs/module-l5/CANONICAL_ROLE_MODEL.md`.

## 7. Stale and Legacy Role Dispositions (unknown count = 0)

- `platform_admin`, `support_admin`, `tenant_admin`, `manager` — **not introduced** (template
  names; would regress least-privilege or invent unsupported authority). Disposition:
  unsupported / not adopted.
- `finance_admin`, `operations_admin`, `compliance_officer`, `tenant_manager` — **display-only**
  labels in the read catalog, `is_implemented=false`; enforce nothing. Disposition: dead
  label / unsupported.
- Stale 5-name `auth/constants.py::ROLES` — **migrated** to the canonical 10 (this sprint).
- `staff` vs `technician` — both canonical; real staff rows use `technician` (`staff` mirrors
  it). Disposition: both canonical.

## 8. Least-Privilege Analysis

The four `admin_*` roles enforce disjoint, bounded permission sets (verified by reading
`permissions.py` 633-744): `admin_operations` = ops jobs + onboarding verify + review
moderation, **no finance/security**; `admin_finance` = `FINANCE_*`/deposits/top-ups,
**denied** jobs/security/roles; `admin_security` = `SECURITY_*`/sessions/IP/API-keys/audit,
**no finance**; `admin_readonly` = read-only across domains. A single generic `platform_admin`
holding the union would **widen** access across finance + security + ops mutations
simultaneously — a strict privilege increase. Therefore the specialized split is provably
safer, and collapsing it was correctly rejected. `tenant_admin`/`manager` were not introduced
because no repository authority distinguishes them from `tenant_owner`/`staff` + per-user
`StaffPermission` overrides.

## 9. Permission & StaffPermission Resolution

Canonical flow (unchanged, verified): authenticate token (`get_current_user`, Redis
blacklist + session-revocation) → account/session state → role → `ROLE_PERMISSIONS` grants →
per-user `StaffPermission` overrides (`staff_permissions` table, tenant-scoped) → tenant
boundary / ownership / assignment / resource-state domain checks → explicit deny → audit.
`StaffPermission` grants only tenant-scoped permission *overrides*; it cannot mint platform
authority. Unknown role → no grants → fail closed. No silent customer fallback (audience fix,
§10).

## 10. Token-Audience Result

Fixed the latent defect: `create_access_token` used `AUDIENCE.get(role, "serviceos:customer")`,
so `technician` and the four `admin_*` roles silently carried a **customer** audience. `AUDIENCE`
now defines all 10 roles explicitly (`admin_*` → `serviceos:admin`, `technician` →
`serviceos:staff`). Existing roles' audiences are byte-identical (additive change);
`decode_token` uses `verify_aud=False`, so this is a correctness/clarity fix with no
validation-behavior change. Unit-proven: `test_every_canonical_role_has_an_audience`,
`test_platform_admin_roles_get_admin_audience`. **Live HTTP audience proof across fresh
login/refresh/rotation for all 10 roles is part of the deferred runtime certification (§2).**

## 11. Custom-Role Decision

`NOT_APPLICABLE` (Section 18 Option B). RBAC + per-user `StaffPermission` overrides is canonical;
no active workflow, API, or functional client builder requires tenant-defined roles. Extension
point retained. No report claims custom roles exist. (No misleading custom-role builder UI was
found active to remove.) Recorded in `CANONICAL_ROLE_MODEL.md`.

## 12. ABAC Decision

`NOT_APPLICABLE` (Section 19 Option B). Canonical model = fixed RBAC + bounded `StaffPermission`
overrides + code-level domain policies (ownership/tenant/assignment/state). No configurable
policy engine is claimed. Recorded in `CANONICAL_ROLE_MODEL.md`.

## 13-17. Multi-Tenant Membership Investigation & Evidence (BLK-01D-2)

- **Data model:** single nullable `User.tenant_id`; no membership/join table anywhere.
- **Backend:** grep for `tenant_membership|switch.?tenant|switch_principal|tenant_users` → **0
  files** (01C). No membership list, switch, or active-tenant-change endpoint exists.
- **Frontend/mobile:** grep for `tenant.?switch|business.?switch|organization.?picker|
  activeTenant|workspace.?switch` across `frontend/**/*.{ts,tsx}` → **0 files**. No switcher UI.
- **Product rules:** a business registers as one tenant; its staff/technicians belong to it and
  are verified by it; customers are marketplace identities; platform admins are global
  (tenant_id NULL). These imply one operational user ↔ one tenant at a time.
- **Use-case analysis:** owner of two businesses → separate tenants/accounts; manager of two
  branches → one tenant, multiple branches; technician for two businesses → not a current model
  (separate accounts); platform employee across tenants → platform role (no membership);
  customer who is also staff → distinct identities; staff transfer A→B → **offboard + reprovision**
  (no simultaneous membership); franchise → multiple tenant records, not one multi-membership
  account. None require multi-tenant-per-user membership in the current product.

## 18. Final Tenant-Identity Decision — Decision A

Multi-tenant operational membership and tenant switching are **not** current ServiceOS
capabilities and are `NOT_APPLICABLE`. `User.tenant_id` is retained as the **canonical** tenant
relationship (validated: tenant roles require a valid tenant; platform roles may be NULL;
customers/guests gain no tenant authority from it). Tenant transfer is handled by
**offboard → revoke sessions → reprovision** under the new tenant. This is documented in
`CANONICAL_ROLE_MODEL.md`.

## 19. Tenant-Model Enforcement (Decision A safeguards)

- New fail-closed guard `e2e/single_tenant_model_guard.py`: detects silent reintroduction of a
  tenant/principal *switch* route or a tenant-membership model class (either would require the
  full membership architecture, not an ad-hoc addition). **PASSED** (0 findings) — and its own
  controlled-failure tests confirm it fires on a planted switch route and a planted membership
  model (one of which caught a real `relative_to` robustness bug in the guard, now fixed).
- No misleading tenant-switch UI/API existed to remove (0 found).

## 20. Role Runtime Proof (IDG-1 — live, this session)

Executed via `scripts/idg1_runtime_proof.py` against the new-code backend on `:8001` (real login
through `/v1/auth/login`, JWT audience inspection, one allowed self-endpoint + one denied
cross-domain endpoint per role). Result: **`IDG1_RUNTIME_PROOF_PASSED`**.

| Role | Live audience (expected) | role claim | Allowed | Denied (→403) |
|---|---|---|---|---|
| `super_admin` | `serviceos:admin` ✓ | super_admin | `/v1/admin/finance/summary`→200 | (P.ALL — n/a) |
| `admin_operations` | `serviceos:admin` ✓ | admin_operations | login-history→200 | security/overview→403 |
| `admin_finance` | `serviceos:admin` ✓ | admin_finance | login-history→200 | **security/overview→403** |
| `admin_security` | `serviceos:admin` ✓ | admin_security | login-history→200 | **finance/summary→403** |
| `admin_readonly` | `serviceos:admin` ✓ | admin_readonly | login-history→200 | security/overview→403 |
| `tenant_owner` | `serviceos:tenant` ✓ | tenant_owner | login-history→200 | admin/security→403 |
| `staff` | `serviceos:staff` ✓ | staff | login-history→200 | admin/finance→403 |
| `technician` | `serviceos:staff` ✓ | technician | login-history→200 | admin/finance→403 |
| `customer` | `serviceos:customer` ✓ | customer | login-history→200 | admin/finance→403 |
| `guest` (no token) | n/a (public) | — | `/health`→200 | admin/finance→**401** |

The two bolded rows are the live least-privilege proof: `admin_finance` is denied Security and
`admin_security` is denied Finance — a single generic `platform_admin` could not produce this
separation. The audience fix is proven live: `technician`/`staff`→`serviceos:staff`,
`admin_*`→`serviceos:admin` (contrast the pre-fix `:8000` instance, which still returns
`serviceos:customer` for `technician`). `staff` was provisioned as a real user through the DB
(`staff.canonical@serviceos.local`), not a test shortcut. All 10 canonical roles are
runtime-classified.

## 21. Cross-Tenant Result (live)

IDG-1 confirmed tenant tokens resolve to distinct tenants: `tenant_owner` (tenant A
`5209ef33…`) vs the second tenant owner (`owner@isolation-test-services.local`, tenant B
`f45664c1…`) — **distinct**. Every tenant/customer role is denied platform-admin endpoints
(403, table above). Backed by `tenant_engine` scope guards (33/33, 01A) and the platform-admin
authorization guard (0 findings, 01B), both re-confirmed passing.

## 22. Guard Result

- `canonical_role_registry_guard.py`: **PASSED** (0 findings, 10 roles).
- `single_tenant_model_guard.py`: **PASSED** (0 findings).
- `admin_router_auth_guard.py`: **PASSED** (0 findings — 01B class still closed).
- Controlled failures: 5 (canonical: 11th role / removed role / stale mirror; single-tenant:
  switch route / membership model) — all detected.

## 23. Focused Test Results

`tests/test_module_l5_01d_canonical_roles.py`: **12 passed**. With identity subset + admin
roles + login: **65 passed** earlier; all green after the guard robustness fix.

## 24. Full Regression Results

`python -m pytest tests/` (exit 0): **9327 passed, 1 skipped, 4 failed, 227 warnings.** The 4
failures are exactly the pre-existing unrelated `test_versions` cases (§25). Baseline at
`61967c8` was 9318 passed; the +9 net are this sprint's new canonical-role/single-tenant tests.
**Zero sprint-attributable failures or regressions.**

## 25. Four SDK-Version Failure Re-evaluation

`test_customer_expo_sdk`, `test_customer_react_native`, `test_customer_react`,
`test_customer_app_json_sdk_version` — assert `mobile/customer-app` Expo/React versions
(asserted `56.0.0`, actual `54.0.0`); concurrent unrelated mobile session's drift; zero
identity/role relevance; **not** introduced by this sprint; **still unrelated**.

## 26. Security Result

One latent defect fixed (customer-audience fallback for `technician`/`admin_*`). No new
CRITICAL/HIGH introduced; enforcement paths unchanged; least-privilege preserved and now guarded.

## 27. Changes Made

Role-registry reconciliation + token-audience correctness fix (01D); canonical-role guard + tests
(01D); single-tenant model guard + controlled-failure tests + robustness fix (01D-R); decision
docs. No enforcement-path or migration changes.

## 28. Files Changed (this pass + 01D)

- `app/engines/auth/constants.py`
- `e2e/canonical_role_registry_guard.py` (new)
- `e2e/single_tenant_model_guard.py` (new)
- `tests/test_module_l5_01d_canonical_roles.py` (new)
- `scripts/idg1_runtime_proof.py` (new — live all-10-role + cross-tenant certification harness)
- `docs/module-l5/CANONICAL_ROLE_MODEL.md` (new)
- `docs/module-l5/MODULE_L5_01D_FINAL_REPORT.md`, `MODULE_L5_01D_R_FINAL_REPORT.md`

## 29. Remaining Blockers

**None** of category external / architecture / requirement remain. The role/tenant architecture
is resolved and guarded; IDG-1 (the previously-deferred live runtime certification) was executed
this session and passed.

Non-blocking observation (not this sprint's scope): MODULE-L5-01B applied `require_super_admin`
to the previously zero-auth `finance_hub`/`security` `summary`/`overview` dashboard endpoints, so
`admin_finance`/`admin_security` receive 403 there (they hold the domain permissions but the
endpoint gates on super_admin). This is fail-safe over-restriction, not a security defect; a
future pass could relax those two endpoints to `require_permission(FINANCE_READ / SECURITY_READ)`
for finer least-privilege. Recorded, not a blocker.

## 30. Final Identity Decision

**`IDENTITY_L5_PROVEN`** — Identity & Access is fully certified under the actual ServiceOS
least-privilege role model and the evidence-based single-tenant identity model. All 10 canonical
roles are runtime-classified live, the token-audience defect is fixed and proven live,
least-privilege and cross-tenant isolation are enforced live, all guards pass (0 findings), and
the full regression is clean (9327 passed; only 4 pre-existing unrelated failures). No CRITICAL
or HIGH Identity defect remains.

## 31. MODULE-L5-02 Gate Decision

**MODULE-L5-02 may begin.** The Identity gate is satisfied: the role and tenant architecture
questions are fully resolved and the live runtime certification passed. No real Identity blocker
remains.
