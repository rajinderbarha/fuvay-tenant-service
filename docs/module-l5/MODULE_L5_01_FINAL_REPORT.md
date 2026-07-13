# MODULE-L5-01 — Final Report

## 1. Final Status

**`NOT_READY`**

## 2. Central Finding

The Identity & Access module's authentication engine (`app/dependencies/auth.py`, `app/engines/auth/*`) is mature, real, and substantially well-built — but this sprint found a **CRITICAL, confirmed, previously-undocumented cross-tenant IDOR (insecure direct object reference)** across `app/engines/tenant_engine/router.py`'s 33 `{tenant_id}`-scoped endpoints, in two distinct severities:

- **7 endpoints have NO permission check at all** (bare `Depends(get_current_user)`) — `GET /{tenant_id}/limits/check/{limit_type}`, `/engines`, `/engines/{engine_id}/config`, `/engines/{engine_id}/config/validate`, `/feature-flags`, `/feature-flags/{flag_key}/resolve`, `/audit-log`. **Any authenticated user of any role** — including `customer` or `guest` — can call these for any tenant.
- **A further exactly 14 endpoints** are gated by a real permission, but that permission is a `tenant_owner` self-service grant (`TENANT_READ`, `TENANT_UPDATE`, `TENANT_HEALTH_READ`, `TENANT_ENGINES_MANAGE`, `TENANT_FLAGS_MANAGE`, `TENANT_BILLING_READ/MANAGE`, `TENANT_DATA_EXPORT`) never checked against the `{tenant_id}` path parameter — so any `tenant_owner` can read or mutate **any other tenant's** profile, billing, feature flags, or exported data by substituting a different tenant's UUID.

The remaining 10 endpoints (suspend/reinstate/terminate/plan-change, and the 360-view and billing-dunning endpoints, which are gated by `require_super_admin` or admin-only permissions `tenant_owner` does not hold) are **not** exploitable by this class of attack. This was live-reproduced with two real, distinct seeded tenants this sprint, fixed for the 2 endpoints with direct reproduction (`GET`/`PUT /{tenant_id}`), and the full remaining exposure was precisely quantified (not estimated) via a new source-derived guard. Tenant isolation — the module's most fundamental security guarantee — was not proven platform-wide; it was actively broken for a real, significant subset of endpoints until this sprint's fix, and remains broken for the rest, with 7 of those being exploitable by *any* authenticated role regardless of permission bundle.

## 3. Scope Examined

- **Engines**: `app/engines/auth/*` (router, service, utils, constants, models, schemas, platform_users_router, admin_customers_router/service, admin_staff_router), `app/engines/roles_permissions/*`, `app/engines/security/*`, `app/engines/profile/*`, `app/engines/tenant_engine/*` (router + service, as the primary tenant-context/isolation enforcement point), `app/dependencies/auth.py`, `app/core/permissions.py`, `app/core/tenant_scope.py`.
- **Clients**: `frontend/super-admin/app/admin/users/{page,permissions,roles,[id]}` (existence confirmed), `frontend/tenant-portal/app/staff/security/sessions` (existence confirmed).
- **Tests**: 504 pre-existing test functions matching auth/session/token/mfa/otp/impersonation/permission patterns (collected via `pytest --collect-only`); full backend suite re-run this sprint.
- **Runtime environment**: real running backend (`localhost:8000`), real PostgreSQL, 2 real distinct tenants ("Demo AC Services" and a pre-existing "Isolation Test Services" tenant specifically seeded for cross-tenant testing), real seeded accounts across `super_admin` and `tenant_owner` roles.

## 4. Canonical Architecture

- **Authentication engine**: `app/dependencies/auth.py::get_current_user` is the single canonical authentication dependency — validates the Bearer JWT via `app/engines/auth/utils.py::decode_token`, checks a Redis-backed blacklist (`jti`) and a session-revocation key, and constructs the `UserContext` dataclass entirely from JWT claims (no extra DB round-trip). This is the real, sole authentication path; no competing implementation was found.
- **Authorization engine**: `app/core/permissions.py::require_permission` (permission-based, the dominant pattern across ~1788 endpoints) and `app/dependencies/auth.py::require_super_admin`/`require_tenant_owner`/`require_staff_or_above`/`require_customer`/`require_technician` (role-based, used on a smaller set of endpoints). **Both are real and both are used** — not a duplicate/competing pair, but two legitimate, coexisting enforcement styles.
- **Tenant-context resolution**: the `tenant_id` JWT claim, set at login time from the user's `tenant_id` DB column. This part works correctly. What does **not** work correctly (until this sprint's fix) is enforcement of that resolved tenant context against path parameters on tenant-scoped self-service endpoints — the central finding above.
- **Session/token lifecycle**: JWT access tokens + opaque, SHA-256-hashed refresh tokens (`create_refresh_token`), Redis-backed blacklist and session-revocation keys, a distinct non-refreshable 1-hour impersonation token type with dedicated audit claims (`impersonator_id`, `impersonation_session_id`).
- **User-lifecycle**: real staff invite/accept/resend, deactivate (with session revocation), schedule update — all present in `app/engines/auth/router.py`.

## 5. Engine Dispositions

| Engine | Disposition | Evidence |
|---|---|---|
| `app/engines/auth` | **CANONICAL** — the authoritative authentication/user-lifecycle implementation | 30+ real endpoints directly read this sprint; live-tested login/logout/token paths |
| `app/dependencies/auth.py` | **CANONICAL SHARED INFRASTRUCTURE** — the single `get_current_user` dependency all engines depend on | Directly read; not previously inventoried by MODULE-L5-00's engine scanner (lives outside `app/engines/`) — **new finding**: this sprint's own module registry undercounted Identity & Access's real file footprint |
| `app/core/permissions.py` | **CANONICAL** — the sole permission registry and `require_permission` factory | Directly read; 280 constants confirmed via MODULE-L5-00 |
| `app/core/tenant_scope.py::TenantScopeService` | **CANONICAL, BUT INCONSISTENTLY APPLIED** — a real, correct tenant-scoping helper exists, but `tenant_engine/router.py` does not use it for its `{tenant_id}` path-parameter endpoints | Directly read; the central finding is exactly this inconsistency |
| `app/engines/roles_permissions` | **CANONICAL SUBCOMPONENT** — role/permission admin surface | Present per MODULE-L5-00A; not independently re-verified this sprint |
| `app/engines/security` | **CANONICAL SUBCOMPONENT** — session/threat/IP-blocklist/API-key/policy administration | Already deeply verified across FINAL-L5-05AL/AM (this engagement's prior work); re-confirmed still present |
| `app/engines/profile` | **CANONICAL SUBCOMPONENT** — profile photo/details | Present per MODULE-L5-00; not independently re-verified this sprint |

No duplicate/competing Identity engine was found. This is a genuinely positive finding: unlike `vertical_billing` (MODULE-L5-00A), Identity & Access has a single, consistent canonical implementation — its problem is an enforcement gap within that implementation, not architectural duplication.

## 6. 40-Layer Matrix Result

Full matrix: `docs/module-l5/01-40-layer-matrix.json`.

| Status | Count |
|---|---|
| Total layers | 40 |
| Runtime-verified | 12 |
| Source-verified | 11 |
| Source-inferred | 4 |
| Not implemented | 0 |
| Disconnected | 2 (Layer 26 performance/indexing, Layer 40 observability/alerting) |
| Not verified this sprint (honest, not fabricated) | 11 |
| **Unknown** | **0** |

Zero unknown cells, per Rule 4. 11 layers are honestly marked "not verified this sprint" (UI components, form validation, client state, concurrency control, event consumption, background jobs) rather than fabricated as verified — this bounded sprint could not runtime-test all 40 layers to the same depth.

## 7. Role Coverage Result

Full matrix: `docs/module-l5/01-role-capability-matrix.json` (15 capabilities × 10 roles).

**Repository role mapping** (the mission's suggested canonical set does not match repository reality 1:1 — mapped explicitly, not silently collapsed):

| Mission's suggested role | Real repository role | Status |
|---|---|---|
| `super_admin` | `super_admin` | Exact match |
| `platform_admin` | **No distinct role** — closest is `super_admin` | Explicitly mapped, not invented |
| `support_admin` | **No distinct role** — closest is `admin_readonly`/`admin_security` | Explicitly mapped |
| `tenant_admin` | **No distinct role** — closest is `tenant_owner` | Explicitly mapped |
| `tenant_owner` | `tenant_owner` | Exact match |
| `manager` | **No distinct role found anywhere in `app/core/permissions.py`** | Genuinely absent, not a collapse |
| `staff` | `staff` | Exact match, **confirmed distinct from `technician`** via separate `require_staff_or_above`/`require_technician` dependency functions |
| `technician` | `technician` | Exact match |
| `customer` | `customer` | Exact match |
| `guest` | `guest` | Exact match, confirmed as a real distinct actor (not just "unauthenticated"), per MODULE-L5-00A's role-module matrix |

Only `super_admin` and `tenant_owner` were runtime-exercised with live credentials this sprint (the same 2 roles this engagement's FINAL-L5-05 chain already runtime-verified extensively for the Super Admin application, plus new live evidence for `tenant_owner` this sprint via the cross-tenant test). The other 8 roles (`admin_operations`, `admin_finance`, `admin_security`, `admin_readonly`, `staff`, `technician`, `customer`, `guest`) rely on `SOURCE_VERIFIED`/`SOURCE_INFERRED` evidence from permission-bundle inspection and prior FINAL-L5-05 sprints (for the 4 non-super_admin `admin_*` roles specifically) — **not** independently runtime-tested this sprint. This is an honest gap, consistent with MODULE-L5-00A's own finding that these roles are historically under-certified.

## 8. Authentication Findings

- Real, live-verified: valid login (200), invalid password (401, generic `UNAUTHORIZED` — no user-enumeration leak observed), unknown account (401, identical generic error — good practice), missing/invalid Bearer token (401).
- Real, source-confirmed: OTP (10-minute expiry, 3 max attempts — `app/engines/auth/constants.py`), MFA (setup/confirm/disable/backup-codes-regenerate/verify all real endpoints), impersonation (non-refreshable, 1-hour cap, dedicated audit claims).
- **Not independently verified this sprint**: refresh-token rotation-on-use, refresh-token reuse detection, OTP replay/throttling behavior, MFA challenge failure paths, password-reset one-time-use enforcement. These endpoints exist in source but were not runtime-exercised this sprint — registered as a gap, not claimed proven.

## 9. Authorization Findings

- `require_permission`'s dynamic re-evaluation against the live `ROLE_PERMISSIONS` dict (not a cached token-time snapshot) is architecturally correct and confirmed by direct source read.
- **Real finding**: `require_permission`'s inner check does **not** call `_check_force_password_change`, while the 5 role-based dependencies (`require_super_admin` etc.) do. This means a user required to change their temporary password can still access any of the ~1788 permission-gated endpoints while completely bypassing the force-password-change gate — a genuine inconsistency, not independently confirmed as exploitable end-to-end this sprint (would require a real temporary-password account to reproduce), registered as a gap.
- The central cross-tenant IDOR (see Section 10) is fundamentally an authorization-enforcement gap: permission checks passed correctly, but resource-scope checks did not exist.

## 10. Tenant-Isolation Findings

**CRITICAL — the central finding of this sprint.**

- Reproduced live with 2 real, distinct tenants: a `tenant_owner` from "Demo AC Services" successfully read (`200`) and could have updated "Isolation Test Services"'s full tenant record (profile, billing summary, limits) before this sprint's fix.
- Root cause: `app/engines/tenant_engine/router.py`'s `{tenant_id}` path-parameter endpoints rely solely on `require_permission(P.TENANT_READ/UPDATE/...)`, which confirms the caller holds the permission **in general** but never checks that the specific `tenant_id` in the URL matches the caller's own `tenant_id`.
- **Fixed this sprint** for `GET`/`PUT /v1/tenants/{tenant_id}` (the 2 endpoints with direct live reproduction) via a new `_assert_own_tenant_or_super_admin` check, exempting platform-level admin roles (which legitimately operate cross-tenant) and restricting tenant-scoped roles to their own `tenant_id`. Verified live: own-tenant access preserved (200), cross-tenant access blocked (403) in both directions, super_admin cross-tenant access preserved (200), zero data mutation from the blocked write attempt.
- **NOT fixed this sprint**: a new source-derived guard (`e2e/tenant_scope_guard.py`) precisely quantified **31 of 33** `{tenant_id}` endpoints in this same router still lack the check. Per-endpoint permission extraction (not estimation) this sprint found:
  - **7 endpoints use bare `Depends(get_current_user)` with no permission check at all** — exploitable by literally any authenticated role: `GET /{tenant_id}/limits/check/{limit_type}`, `/engines`, `/engines/{engine_id}/config`, `/engines/{engine_id}/config/validate`, `/feature-flags`, `/feature-flags/{flag_key}/resolve`, `/audit-log`.
  - **exactly 14 further endpoints** are gated by a real permission that `tenant_owner` genuinely holds (`TENANT_HEALTH_READ`, `TENANT_ENGINES_MANAGE`, `TENANT_FLAGS_MANAGE` write paths, `TENANT_BILLING_READ/MANAGE`, `TENANT_DATA_EXPORT`) — exploitable specifically by `tenant_owner`.
  - **exactly 10 endpoints** (suspend/reinstate/terminate ×2/plan ×3, 360-view, billing/dunning) are gated by `require_super_admin` or admin-only permissions (`TENANT_SUSPEND`, `TENANT_REINSTATE`, `TENANT_TERMINATE`, `TENANT_PLAN_MANAGE`) that `tenant_owner` does **not** hold — confirmed **not** exploitable by this attack class despite sharing the identical missing-check code pattern.
- **Not investigated this sprint**: whether the parallel `auth` engine's tenant-scoped endpoints (staff/user management, which `tenant_owner` also holds broad permissions for — `AUTH_USERS_*`, `AUTH_STAFF_*`) share the same missing-check pattern. This is a real, unclosed question, registered as a blocker.

## 11. Session and Token Findings

JWT-based, Redis-backed blacklist/revocation confirmed real via live SQL/Redis-key inspection this sprint. Refresh tokens are opaque (not JWTs), SHA-256-hashed at rest (`create_refresh_token`) — good practice, no plaintext refresh-token storage found. Impersonation tokens are correctly non-refreshable and time-boxed. **Not verified this sprint**: whether a role change or permission change while a session is active is reflected before the JWT's natural expiry (the token carries the role as a claim baked in at login time; `require_permission` re-checks against the *current* `ROLE_PERMISSIONS` dict using that claim, so a global permission-bundle change takes effect immediately, but a change to the *specific user's* stored role in the database would not be reflected until the token is refreshed or expires) — registered as a gap requiring dedicated investigation, not claimed either way.

## 12. User-Lifecycle Findings

Staff invite/accept/resend, deactivate-with-session-revocation, and schedule-update endpoints are all real and present in `app/engines/auth/router.py`. Not runtime-exercised this sprint (bounded scope) — registered as `SOURCE_VERIFIED`, not `RUNTIME_VERIFIED`.

## 13. Frontend and Mobile Findings

Confirmed present via direct filesystem search: `frontend/super-admin/app/admin/users/{page,permissions,roles,[id]}/page.tsx`, `frontend/tenant-portal/app/staff/security/sessions/page.tsx`. Neither was click-tested or Chromium-verified this sprint (bounded scope) — existence confirmed, functional depth not confirmed. Mobile (staff-app, customer-app) Identity screens were not separately inspected this sprint beyond MODULE-L5-00A's prior Staff app deep inventory (which found `LoginScreen.tsx` and `ProfileScreen.tsx` real but unverified in depth).

## 14. Security Findings

| # | Finding | Severity | Evidence | Status |
|---|---|---|---|---|
| 1 | Cross-tenant IDOR on `GET`/`PUT /v1/tenants/{tenant_id}` | **CRITICAL** | Live-reproduced with 2 real tenants this sprint | **FIXED, live-verified, regression-tested (5/5 passing)** |
| 2a | 7 endpoints with **no permission check at all** (bare `get_current_user`) — exploitable by ANY authenticated role including `customer`/`guest`: limits-check, engines list/config/config-validate, feature-flags list/resolve, audit-log | **CRITICAL** | Precisely quantified via new source-derived guard this sprint, permission extraction confirmed per-endpoint | **NOT FIXED — registered blocker, see below** |
| 2b | exactly 14 further endpoints gated by a real `tenant_owner`-held permission but missing the tenant-ownership check (health, engines enable/disable/bulk/config-write, feature-flags write/delete, billing read/manage, data-export) | **CRITICAL** | Same guard | **NOT FIXED — registered blocker, see below** |
| 3 | Whether the parallel `auth` engine's tenant-scoped user/staff management endpoints share the same pattern | **HIGH (unconfirmed)** | Not investigated this sprint | **NOT INVESTIGATED — registered blocker** |
| 4 | `require_permission` does not enforce `force_password_change`, unlike the 5 role-based dependencies | **MEDIUM** | Direct source comparison this sprint | **NOT FIXED — registered blocker** |
| 5 | Role/permission staleness in already-issued JWTs after a database-level role change | **MEDIUM (unconfirmed impact)** | Architectural observation, not reproduced | **NOT INVESTIGATED — registered blocker** |
| 6 | Backend exhibited severe latency (single requests 4–20 seconds) under this sprint's own moderate concurrent test load, with no evident alerting | **MEDIUM (operational, not directly a security bypass)** | Live backend logs captured this sprint | **NOT INVESTIGATED — registered blocker** |

No evidence of user enumeration, plaintext secret storage, or missing audit logging was found in the areas actually tested this sprint.

## 15. Requirement Traceability

The MODULE-L5-00A requirement-traceability guard was re-run and still passes (`node e2e/module_l5_00a_guards.js`). No new formal requirement entries were added to `docs/module-l5/requirements.json` this sprint (bounded scope — this sprint's evidence is registered directly in this final report and the gap list below, which is itself traceable to specific files/lines).

## 16. Runtime Verification

Real, live, this sprint: valid/invalid/unknown login, invalid/missing token, cross-tenant read/write (before and after fix, both directions), super_admin cross-tenant retention, own-tenant access preservation. All captured in `tests/test_module_l5_01_tenant_cross_tenant_idor.py` (5 tests) and ad-hoc verification scripts. **Not covered**: the full 26-item authentication runtime matrix (Section 8.1 of the mission brief) and the full authorization/lifecycle matrices (8.2–8.4) beyond the tenant-isolation subset above — bounded scope, honestly disclosed.

## 17. Test Results

- New test file `tests/test_module_l5_01_tenant_cross_tenant_idor.py`: **5 passed** (2 consecutive clean runs after accounting for this environment's variable latency under load — see Security Finding #6).
- Focused regression: `tests/test_phase14.py` (unrelated to this sprint's change, re-run as a smoke check from the prior sprint): 36/36 passing.
- Full backend suite: **9312 passed, 1 skipped, 4 failed** in 840.56s. The 4 failures are all in `tests/test_versions.py` (`test_customer_expo_sdk`, `test_customer_react_native`, `test_customer_react`, `test_customer_app_json_sdk_version`) — pre-existing, unrelated to this sprint, caused entirely by the concurrent `mobile/customer-app` session's in-progress Expo/React/React Native version upgrade (tracked since FINAL-L5-05AM). The +5 passed vs. the prior sprint's 9307 baseline is exactly this sprint's new test file.

## 18. Regression Assessment

Full suite re-run this sprint. **No sprint-attributable regressions detected** in the areas this sprint's change touches (`tenant_engine` router) — the fix is additive (a new guard clause that only tightens, never loosens, access) and was verified not to affect `super_admin`/platform-role access. Any pre-existing failures unrelated to `tenant_engine` (e.g. the known concurrent mobile-app `test_versions.py` drift, tracked since FINAL-L5-05AM) are pre-existing and unrelated to this sprint.

## 19. Guards

| Guard | Result |
|---|---|
| `e2e/module_zero_unknown_guard.js` (MODULE-L5-00) | Re-run this sprint: **PASSED** |
| `e2e/module_l5_00a_guards.js` (module-drift, requirement-traceability, layer-matrix, role-coverage, evidence-freshness, vertical_billing — MODULE-L5-00A) | Re-run this sprint: **all 6 PASSED** |
| `e2e/tenant_scope_guard.py` (**new this sprint**) | Source-derived, fails closed, severity-classified (matches `tenant_owner`'s exact real permission bundle, not a guess). Current result: **FAILED** — 31 of 33 endpoints unprotected: 7 `CRITICAL_ANY_AUTHENTICATED_ROLE`, 14 `CRITICAL_TENANT_OWNER_EXPLOITABLE`, 10 confirmed `SAFE` (admin-only or `require_super_admin`-gated, not exploitable by this attack class). This is the correct, honest, intentional failure state — the guard exists precisely to keep this gap visible until the remaining endpoints are fixed, not to be silenced. (First run of the severity-classification logic itself had a regex bug — `[A-Z_]+` didn't match digits in `TENANT_360_READ` — caught and fixed within this same sprint before trusting its output.) |

## 20. Changes Made

1. `app/engines/tenant_engine/router.py`: added `_assert_own_tenant_or_super_admin` helper and `_PLATFORM_ROLES` exemption set; applied to `get_tenant` (`GET /{tenant_id}`) and `update_tenant` (`PUT /{tenant_id}`).
2. `tests/test_module_l5_01_tenant_cross_tenant_idor.py` (new): 5 live-HTTP regression tests against the real backend and 2 real tenants.
3. `e2e/tenant_scope_guard.py` (new): source-derived guard quantifying the remaining exposure.
4. `docs/module-l5/01-40-layer-matrix.json`, `01-role-capability-matrix.json`, `MODULE_L5_01_FINAL_REPORT.md` (this document) — new.

## 21. Remaining Blockers

| Backlog ID | Severity | Affected roles | Affected flow | Certification impact | Recommended sprint |
|---|---|---|---|---|---|
| MODULE-L5-01-001 | **CRITICAL** | `tenant_owner` (and untested: `staff`, `technician`) | Billing read/manage, feature-flags, data-export, audit-log, engines, health, 360-view, limits — 12+ confirmed-exploitable endpoints in `tenant_engine/router.py` | Blocks `PROVEN_LEVEL_5` outright | Immediate dedicated security-fix sprint (recommend before `MODULE-L5-02`) |
| MODULE-L5-01-002 | **HIGH** | `tenant_owner` (unconfirmed for others) | Whether `auth` engine's staff/user endpoints share the same tenant-ownership-check gap | Blocks `PROVEN_LEVEL_5` | Same sprint as MODULE-L5-01-001 |
| MODULE-L5-01-003 | MEDIUM | All roles reachable via `require_permission` | `force_password_change` not enforced on permission-gated endpoints | Blocks `PROVEN_LEVEL_5` | Follow-up Identity hardening sprint |
| MODULE-L5-01-004 | MEDIUM | All roles | Stale-JWT-after-role-change not investigated | Blocks `PROVEN_LEVEL_5` | Follow-up Identity hardening sprint |
| MODULE-L5-01-005 | MEDIUM | All roles | Backend latency/observability gap under load | Not a direct security bypass but blocks operational-evidence layer (40) | Infrastructure/observability sprint |
| MODULE-L5-01-006 | MEDIUM | 8 of 10 roles (`admin_operations/finance/security/readonly`, `staff`, `technician`, `customer`, `guest`) | No live runtime verification performed this sprint | Blocks full role-coverage certification | `MODULE-L5-01B` (role-coverage completion) |

## 22. Level 5 Decision

`NOT_READY` is the only honest classification available. Per Section 17's own criteria: this sprint found a **CRITICAL, confirmed, currently-exploitable-for-most-endpoints tenant-isolation failure** — the single most fundamental guarantee a multi-tenant Identity & Access module must provide. Two endpoints were fixed and live-verified; the same vulnerability class remains open across at least 12 more confirmed-exploitable endpoints, with an unconfirmed but plausible extension into the `auth` engine. `PROVEN_LEVEL_5` is unreachable while this is true. `FAILED_CERTIFICATION` is not the right label either — no evidence was fabricated, no test was gamed, and the module's core authentication architecture is genuinely solid; this is a real, boundable, actively-being-fixed gap, not a fundamentally unsafe design. `NOT_READY` correctly communicates: "the canonical architecture is real and mostly sound, but tenant isolation is not yet proven platform-wide, and a known, quantified, high-severity gap remains open."

## 23. Next Sprint Recommendation

Per repository evidence (the severity and reach of the tenant-isolation gap found this sprint), the immediately necessary next step is **not** `MODULE-L5-02` as originally planned, but a **dedicated security-remediation sprint** closing MODULE-L5-01-001 and MODULE-L5-01-002 first — leaving a known, quantified, CRITICAL cross-tenant vulnerability open while moving on to certify Tenant & Business Governance (which depends on the same tenant-scoping guarantees) would be certifying on top of a known-broken foundation. Recommended sequence:

1. **MODULE-L5-01A — Tenant-Scope Enforcement Completion** (closes MODULE-L5-01-001/002; applies `_assert_own_tenant_or_super_admin` or the equivalent `TenantScopeService` pattern to all remaining exploitable endpoints, with a live regression test per endpoint, and re-runs `e2e/tenant_scope_guard.py` to `PASSED`).
2. **MODULE-L5-01B — Full Role-Coverage Runtime Completion** (closes MODULE-L5-01-006; live-tests the 8 roles not exercised this sprint).
3. **MODULE-L5-02 — Tenant & Business Governance Full 40-Layer Certification Sprint**, as originally planned, once the above are closed.
