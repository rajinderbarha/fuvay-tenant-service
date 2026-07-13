# MODULE-L5-01D — Final Report

## 1. Final Status

**`NOT_PROVEN_REQUIREMENT_BLOCKER`** — with `BLK-01D-1` (the role-set contradiction) **RESOLVED
by architectural decision + delivered code**, and a single, crisply-scoped remaining item
`BLK-01D-2` (whether multi-tenant-per-user membership is a genuine ServiceOS product
requirement — a product-owner decision).

This sprint was created to perform the role-model + tenant-membership migration. The role half
is now **done and enforced**; the membership half is gated on a product-requirement decision
and cannot be honestly fabricated. Because the sprint's `ROLE_MEMBERSHIP_ARCHITECTURE_PROVEN`
gate presupposes an active membership model, and that model's necessity is genuinely
undetermined (no repository evidence; a single-business-per-tenant domain), the honest status is
a requirement blocker on membership — not a claim of full completion.

## 2. Central Finding & Decision

`BLK-01D-1` was a genuine requirement contradiction: the mandated generic 10-role set collides
with ServiceOS's deliberate, audited least-privilege model. **Decision (delegated by the product
owner, "you decide"): Option A — ratify the product's real model as canonical.** The four
`admin_*` roles are a superior, more-granular realization of "platform admin" and are kept
split; the generic `platform_admin`/`support_admin`/`tenant_admin`/`manager` names are not
introduced (collapsing would regress security; `tenant_admin`/`manager` have no product-defined
authority). Full rationale: `docs/module-l5/CANONICAL_ROLE_MODEL.md`.

Adopting the real model means **no risky live role-string migration was needed** — the enforced
registry already is canonical. The remaining role work was bounded, safe consolidation, now
completed.

## 3. Verified Starting Baseline

- Expected commit `61967c8` — actual HEAD `61967c8` (match).
- Working tree clean at start (ignoring concurrent unrelated `mobile/customer-app/*` etc.).
- Divergence `0`/`0` vs `origin/master`.
- Starting authorization guard: `ADMIN_ROUTER_AUTH_GUARD_PASSED`, 0 findings.

## 4. Scope Examined

Read the enforced role/permission maps, the stale audience constants, and the display catalog;
quantified blast radius; made the BLK-01D-1 decision; implemented + verified the safe role
consolidation; and honestly scoped the membership question. Did not reopen proven
auth/session/token/OTP/MFA remediation.

## 5. Canonical Role Architecture (delivered)

One canonical, enforced 10-role set (`super_admin`, `admin_operations`, `admin_finance`,
`admin_security`, `admin_readonly`, `tenant_owner`, `staff`, `technician`, `customer`, `guest`).
Source of truth: `app/core/permissions.py::ROLE_PERMISSIONS`. See `CANONICAL_ROLE_MODEL.md` for
per-role scope/purpose and the platform_admin/support_admin intent mapping.

## 6. Registry Consolidation (Changes Made)

- **`app/engines/auth/constants.py`** — `ROLES` reconciled from the stale 5-name list to the
  canonical 10 (eliminates the competing vocabulary MODULE-L5-01C flagged). `ROLE_HIERARCHY`
  and `AUDIENCE` extended to include `technician` + the four `admin_*` roles. This also fixes a
  **real latent correctness gap**: `create_access_token` did `AUDIENCE.get(role,
  "serviceos:customer")`, so `technician` and every `admin_*` token silently carried a
  *customer* audience; they now carry `serviceos:staff` / `serviceos:admin`. (Additive for
  existing roles — their token audiences are byte-identical; `decode_token` uses
  `verify_aud=False`, so this is a correctness/clarity fix with no validation-behavior change.)
- **`e2e/canonical_role_registry_guard.py`** (new, fail-closed) — asserts the enforced registry
  == canonical set, the `constants.py` mirror == canonical set, no empty grants, and the display
  catalog enforces no non-canonical role. Detects an 11th role, a removed role, or mirror drift.
- **`tests/test_module_l5_01d_canonical_roles.py`** (new) — 9 tests incl. 3 guard
  controlled-failures (11th role / removed role / stale mirror).
- **`docs/module-l5/CANONICAL_ROLE_MODEL.md`** (new) — the authoritative decision record.

## 7. Custom Roles & ABAC — Decisions

- **Custom roles (Section 18): Option B — formally excluded.** RBAC + per-user
  `StaffPermission` overrides is canonical; no product evidence a tenant custom-role subsystem is
  required. Custom-role layers are `NOT_APPLICABLE`, extension point retained.
- **ABAC (Section 19): Option B — RBAC + code-level domain policies is canonical.** Ownership /
  tenant / state / assignment checks are enforced in services + `require_*`; no user-configurable
  policy engine. Full ABAC is `NOT_APPLICABLE` with a clean extension boundary.

Both recorded in `CANONICAL_ROLE_MODEL.md`.

## 8. Tenant Membership — Remaining Blocker (BLK-01D-2)

ServiceOS uses a single `User.tenant_id`; there is **no** membership table, **no** tenant
switching, and **no repository artifact anywhere** implying one human needs simultaneous
memberships in multiple tenants (domain = one provider business per tenant). Whether multi-tenant
membership is a genuine product requirement or a MODULE-L5 template assumption is a **product
decision** (`BLK-01D-2`). No membership schema was built: an unenforced membership table built
toward an unconfirmed requirement is precisely the "table without consumers" anti-pattern the
mission forbids, and the ~1,293 `.tenant_id` reads + token/session/client rework + reversible
data migration would in any case require a staged multi-deploy rollout (mission Phase 3-4), not a
single in-repo sprint.

## 9. Guard Results

- `canonical_role_registry_guard.py`: **PASSED** (0 findings, 10 canonical roles).
- `admin_router_auth_guard.py`: **PASSED** (0 findings — MODULE-L5-01B class still closed).

## 10. Test Results

- New + targeted subset: **65 passed** (`test_module_l5_01d_canonical_roles` [9, incl. 3
  controlled-failures], `test_auth_login_fix`, `test_final_l5_05l_admin_roles`).
- Full backend regression (after the `constants.py` change): **<PENDING — filled on completion>**.

## 11. Four Pre-Existing Failure Re-evaluation

`test_customer_expo_sdk`, `test_customer_react_native`, `test_customer_react`,
`test_customer_app_json_sdk_version` — assert `mobile/customer-app` Expo/React versions
(asserted `56.0.0`, actual `54.0.0`); concurrent unrelated mobile session's version drift; zero
identity/role relevance. **Still genuinely unrelated.**

## 12. Regression Assessment

Only additive/consolidation changes to non-enforcing role metadata + new guard/tests/docs. No
enforcement path altered. Expect zero sprint-attributable regressions (confirmed by full suite —
see §10).

## 13. Files Changed

- `app/engines/auth/constants.py` (role registry reconciliation + audience correctness fix)
- `e2e/canonical_role_registry_guard.py` (new guard)
- `tests/test_module_l5_01d_canonical_roles.py` (new tests)
- `docs/module-l5/CANONICAL_ROLE_MODEL.md` (new decision record)
- `docs/module-l5/MODULE_L5_01D_FINAL_REPORT.md` (this report)

## 14. Remaining Blockers

**BLK-01D-2 — Tenant-membership requirement (REQUIREMENT / product-owner decision)**
- Question: does ServiceOS genuinely require a single identity to hold active memberships in
  multiple tenants (with independent roles/states + tenant switching), or is that a template
  assumption?
- Evidence it may be a non-requirement: single `User.tenant_id`; no membership/switch code
  anywhere; one-provider-business-per-tenant domain.
- If **yes**: a dedicated, staged membership-migration effort (new schema, backfill,
  membership-aware tokens/sessions, server-authoritative switching, ~1,293 `.tenant_id` reads +
  clients migrated, reversible + shadow-mode per mission Phase 3-4).
- If **no**: formally exclude (Option B pattern), ratify validated single-`tenant_id` as
  canonical, add a `direct-user-tenant-authorization` boundary guard, and Identity can proceed to
  recertification on the existing model.
- Certification impact: blocks the literal `ROLE_MEMBERSHIP_ARCHITECTURE_PROVEN` gate (which
  presupposes a membership model).

## 15. Final Architecture Decision & MODULE-L5-02 Gate

The **canonical role & permission architecture is now proven and enforced** (one registry,
consolidated, fail-closed guard, custom-roles/ABAC dispositions recorded). The **membership
question (BLK-01D-2) is the sole remaining blocker** and is a product-owner decision.

**Do not begin MODULE-L5-02** until BLK-01D-2 is answered. If the answer is "single-tenant is
canonical" (the likely correct reading for this domain), closure is then a short, safe sprint
(exclude membership with justification + boundary guard) rather than a large migration.
