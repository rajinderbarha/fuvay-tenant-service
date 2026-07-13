# MODULE-L5-01D — Final Report

## 1. Final Status

**`NOT_PROVEN_REQUIREMENT_BLOCKER`**

The migration this sprint was created to perform cannot be executed honestly or safely because
its **target is contradictory at the requirement level**. Section 4.1 mandates that the *only*
canonical system-role codes be a specific generic set (`super_admin, platform_admin,
support_admin, tenant_admin, tenant_owner, manager, staff, technician, customer, guest`) and
that legacy values "must not remain independent active vocabularies." But ServiceOS's actual,
enforced role model is a **deliberate, audited least-privilege design** — `super_admin` plus
four separately-permissioned platform roles (`admin_operations`, `admin_finance`,
`admin_security`, `admin_readonly`) built and rationalized line-by-line across the prior
FINAL-L5-05L…05U sprint series. Conforming to Section 4.1 forces one of two outcomes, both
prohibited by this same mission and by basic security practice:

1. **Collapse** the four least-privilege roles into a single generic `platform_admin` →
   a real privilege-escalation / security **regression** (Section 8 "do not collapse blindly",
   Section 29 "role escalation" / "platform-role downgrade preserving old access").
2. **Invent** `tenant_admin` and `manager` (and split `platform_admin`/`support_admin`) with
   authority boundaries that **no repository or product evidence defines** — "unsafe to infer"
   (the mission's own REQUIREMENT_BLOCKER trigger).

Resolving this requires a **product-owner decision** on the canonical role set — specifically
whether ServiceOS abandons its audited least-privilege admin split in favour of the generic
names, or whether the required role list should be amended to match the product's real,
more-granular model. That decision is a prerequisite input, not something safe to fabricate.
The tenant-membership migration (also required) is a large but *downstream* effort that cannot
even be correctly targeted until the role set is fixed.

This is reported as a requirement blocker — an explicitly allowed outcome — rather than
executing an unsafe live cutover that would regress a deliberate security design, or
fabricating a "PROVEN" result for a migration that was not actually completed.

## 2. Central Finding

**The MODULE-L5-01C "three competing role registries" framing was partly an overstatement and
is corrected here** (the mission requires reconciliation, not blind inheritance). The true
state:

| Registry | Role of the file | Enforcing? |
|---|---|---|
| `app/core/permissions.py::ROLE_PERMISSIONS` | **The single authoritative RBAC registry** — 10 enforced keys: `super_admin, tenant_owner, staff, technician, customer, guest, admin_operations, admin_finance, admin_security, admin_readonly` | **YES** — every `require_permission`/`require_*` resolves here |
| `app/engines/auth/constants.py::ROLES` | Stale 5-name list feeding token `AUDIENCE` / `ROLE_HIERARCHY` | No — audience/hierarchy metadata only; not an enforcement path |
| `app/engines/roles_permissions/service.py` | **Read-only display catalog** for the admin Roles UI; reads *from* `ROLE_PERMISSIONS`, surfaces non-existent names with `is_implemented=false` (its own docstring: "intentionally honest, not a bug") | No — pure read/display |

So there is **one** enforced role vocabulary, not three. The genuine defects are (a) the stale
5-name `constants.py::ROLES` audience list (a bounded, real drift) and (b) the fact that the
one enforced set does not use the mission's mandated *names*. The enforced set is not sloppy —
it is a deliberate least-privilege realization. Evidence (read directly this sprint,
`permissions.py` lines 633-744): each `admin_*` role carries an explicit, commented,
non-overlapping permission set with recorded rationale (e.g. `admin_finance` is granted
`FINANCE_*`/`FINANCE_DEPOSITS_*` and *explicitly denied* `ADMIN_JOBS_*`, `SECURITY_*`,
`PLATFORM_ROLES/PERMISSIONS`; `admin_readonly` holds only read grants). Collapsing these into
one `platform_admin` destroys that separation.

## 3. Verified Starting Baseline

- **Expected commit:** `61967c8` — **actual HEAD:** `61967c8` (match).
- **Working-tree state:** clean (ignoring concurrent unrelated `mobile/customer-app/*`,
  `docs/customer-app/*`, `e2e/docs/*`). This sprint adds only this report.
- **Branch divergence:** `0` ahead / `0` behind `origin/master`.
- **Authorization-guard starting result:** `ADMIN_ROUTER_AUTH_GUARD_PASSED`, 0 findings
  (MODULE-L5-01B platform-admin class remains closed).

## 4. Scope Examined

Read the actual enforced role/permission maps (`app/core/permissions.py`), the stale audience
list (`auth/constants.py`), and the display catalog (`roles_permissions/service.py`) to ground
the analysis in code rather than inference. Quantified the migration blast radius by mechanical
count. Consumed the MODULE-L5-01C report and `BLK-01C-1`. Did **not** re-open proven
authentication/session/token/OTP/MFA/lockout/password remediation (no regression evidence).

## 5. Migration Blast Radius (quantified)

- **`.tenant_id` references in `app/` (Python):** **1,293** occurrences. A representative
  fraction are authorization/filtering reads that Section 10 requires migrating off
  `User.tenant_id` as an authority source.
- **Enforced role-string literal consumers in `app/`:** **389** occurrences of the ten
  canonical/legacy role names.
- **Frontend:** role strings are largely centralized (only 2 occurrences of the sampled admin
  role names in `frontend/super-admin`), which is good — but the tenant-portal and 3 web apps
  plus 2 mobile apps still require a per-client audit the mission mandates.
- **Backend test surface:** 9,318 passing tests, a large share of which seed and assert on the
  current role strings and single-`tenant_id` model.

Introducing a first-class tenant-membership model (new table, backfill, membership-aware
tokens/sessions, server-authoritative switching) and re-pointing ~1,293 tenant-context reads +
389 role consumers + all client guards, then **runtime-proving all 10 roles + reversible data
migration + rollback** on a live system of this size, is not safely completable *and provable*
in a single in-repo sprint. Per the mission's own Phase 3-4 (Section 22), a safe cutover
requires shadow-mode decision comparison and controlled stale-token expiry — inherently a
staged, multi-deploy rollout, not a single sprint. (This is the ARCHITECTURE dimension; it is
gated behind, and secondary to, the §1 requirement contradiction.)

## 6. Legacy-Role Ledger (Section 7 deliverable)

| Legacy value | Source / status | Meaning today | Honest target disposition | 1:1? |
|---|---|---|---|---|
| `super_admin` | enforced | Sole `P.ALL` wildcard | Canonical `super_admin` (unchanged) | Yes |
| `admin_operations` | enforced (least-privilege) | Ops jobs, tenant onboarding verify, reviews moderate, ops dashboards; **no finance/security** | Realization of "platform_admin (operations)". Collapse to generic `platform_admin` = **over-grant/regression** → BLOCKED pending decision | No — split |
| `admin_finance` | enforced (least-privilege) | `FINANCE_*`, deposits, topups; **denied** jobs/security/roles | Realization of "platform_admin (finance)". Same blocker | No — split |
| `admin_security` | enforced (least-privilege) | `SECURITY_*`, sessions revoke, IP blocklist, API keys, audit read | Realization of "platform_admin (security)" / partly `support_admin` | No — split |
| `admin_readonly` | enforced (least-privilege) | Read-only across ops/finance/security/tenant | Realization of "platform_admin (read-only)" / `support_admin` read tier | No — split |
| `staff` | enforced but unpopulated (comment: mirrors `technician`) | Tenant operational | Canonical `staff` — but real rows use `technician` | Needs data check |
| `technician` | enforced, actually seeded on real staff rows | Tenant assignment-scoped | Canonical `technician` | Yes |
| `tenant_owner` | enforced | Tenant top authority | Canonical `tenant_owner` | Yes |
| `customer`, `guest` | enforced | Self / public | Canonical (unchanged) | Yes |
| `ROLES` list (`auth/constants.py`) | stale audience/hierarchy (5 names) | Token audience map | Reconcile to enforced set (bounded fix) | n/a |
| `platform_admin`,`finance_admin`,`operations_admin`,`support_admin`,`compliance_officer`,`tenant_manager` (`roles_permissions/service.py`) | **display-only**, `is_implemented=false` | UI catalog placeholders | Not enforced; align catalog to final decided set | n/a |

**Two required canonical roles (`tenant_admin`, `manager`) map from *nothing*** — they have no
legacy source, no permission set, and no product-defined authority. Their existence and exact
boundaries (Section 33 Q18-21: "exact difference between tenant_admin and manager", etc.) are
**genuinely unavailable** in the repository.

## 7. Answers to Mandatory Questions (the honestly-answerable subset)

- **Q1 (single canonical registry?):** Enforcement already has one — `ROLE_PERMISSIONS`. Its
  *names* don't match the mandate.
- **Q4-7 (what happened to admin_operations/finance/security/readonly?):** **Nothing this
  sprint.** They remain the enforced, audited least-privilege platform roles. Collapsing them
  into generic `platform_admin`/`support_admin` is the *blocked* action (regression risk).
- **Q8-11 (finance_admin/operations_admin/compliance_officer/tenant_manager?):** These exist
  only as `is_implemented=false` labels in the display catalog; they enforce nothing.
- **Q18-21 (exact role distinctions):** `tenant_owner` is defined and enforced; `tenant_admin`
  and `manager` **do not exist** and have no product-defined authority to distinguish — this is
  the core requirement gap.
- **Q23-24 (`User.tenant_id` disposition):** Still authoritative today across ~1,293 reads;
  disposition cannot be chosen safely until the membership model is designed against a fixed
  role set.
- **Q64-66 (architecture proven? Identity recert? may 02 begin?):** No / No / **No.**

## 8. Why no code was changed (and why that is the correct, responsible action)

The mission lists "adding a membership table without migrating consumers," "creating an alias
map with no data migration," and "adding custom-role tables without enforcement" as explicitly
**insufficient** outcomes. Building any of those now would produce exactly that dead,
unenforced, security-sensitive scaffolding — and worse, it would be built toward a **target
that is not yet decidable** (the canonical role set is contradictory). Writing a role migration
that collapses audited least-privilege roles, or that invents `tenant_admin`/`manager`
authority from nothing, would regress security or encode unsafe inferences. The responsible
engineering action when the target itself is contradictory is to **stop and surface the
decision**, not to generate motion. No production code was touched; the guard remains at 0
findings and the system remains in its verified-good state.

## 9. Test Results & Four-Failure Re-evaluation

- Identity-focused subset (re-run at this baseline in 01C): **168 passed, 0 identity failures.**
  No code changed since, so unchanged.
- Full suite at `61967c8`: 9,318 passed / 1 skipped / 4 failed.
- **Four `test_versions` failures** (`test_customer_expo_sdk`, `test_customer_react_native`,
  `test_customer_react`, `test_customer_app_json_sdk_version`): re-confirmed — assert
  `mobile/customer-app` Expo/React versions (asserted `56.0.0`, actual `54.0.0`); a concurrent
  unrelated mobile session's version drift. Zero identity/role/membership relevance.
  **Still genuinely unrelated**, not blindly inherited.

## 10. Regression Assessment

Zero sprint-attributable changes (report-only). Guard passes; no regression.

## 11. Changes Made / Files Changed

- `docs/module-l5/MODULE_L5_01D_FINAL_REPORT.md` (new). No code changes.

## 12. Remaining Blockers

**BLK-01D-1 — Canonical role-set requirement contradiction (REQUIREMENT)**
- Severity: HIGH (blocks the entire migration; not a live defect — current system is coherent
  and more-granular than the mandate).
- Affected: role registry, all platform-admin roles, `tenant_admin`/`manager` definition, and
  (downstream) the entire membership/token/session/consumer migration.
- Exact evidence: Section 4.1 mandates 10 generic role codes as the *only* canonical set and
  forbids independent legacy vocabularies; the enforced model is a deliberate least-privilege
  split (`admin_operations/finance/security/readonly`, `permissions.py` lines 633-744 with
  per-role deny rationale). Conforming forces privilege escalation (collapse) — forbidden by
  Section 8/29 — or invented authority for `tenant_admin`/`manager` — forbidden as "unsafe to
  infer." `tenant_admin` and `manager` have no source in the repo.
- Why it cannot be safely completed: the migration target is undecidable without a product
  decision; any choice made unilaterally regresses security or fabricates privileged-role
  boundaries.
- Exact prerequisite: a product-owner decision — either (a) amend the required role list to
  ratify the product's real model (`super_admin` + 4 least-privilege platform roles + tenant
  roles), or (b) explicitly accept collapsing the least-privilege split into generic
  `platform_admin`/`support_admin` and author the exact authority of `tenant_admin`/`manager`.
- Certification impact: blocks `ROLE_MEMBERSHIP_ARCHITECTURE_PROVEN`.

**BLK-01D-2 — Tenant-membership migration scope/safety (ARCHITECTURE, downstream of BLK-01D-1)**
- Severity: HIGH. Evidence: ~1,293 `.tenant_id` reads + 389 role consumers + membership-aware
  token/session redesign + 3 web + 2 mobile clients + reversible data migration + all-10-role
  runtime proof. The mission's own Phase 3-4 requires shadow-mode + staged token expiry — a
  multi-deploy rollout. Prerequisite: BLK-01D-1 resolved, then a staged migration executed
  across multiple controlled deploys, not a single in-repo sprint.

## 13. Final Architecture Decision

Identity role/membership architecture is **not proven**. The current enforced model is coherent
and deliberately least-privilege; the blocker is that the mandated canonical role *set*
contradicts it and cannot be reconciled without a product decision, and the downstream
membership migration cannot be safely cut over in one sprint. Status:
**`NOT_PROVEN_REQUIREMENT_BLOCKER`**.

## 14. Identity Recertification Recommendation & MODULE-L5-02 Gate

**Do not begin MODULE-L5-02.** Required next step: a product-owner decision resolving BLK-01D-1
(the canonical role set), after which a dedicated, *staged* membership-migration effort
(BLK-01D-2) can proceed against a fixed target with shadow-mode comparison and controlled
token expiry — and only then can Identity target `ROLE_MEMBERSHIP_ARCHITECTURE_PROVEN` and the
subsequent `IDENTITY_L5_PROVEN` recertification honestly.
