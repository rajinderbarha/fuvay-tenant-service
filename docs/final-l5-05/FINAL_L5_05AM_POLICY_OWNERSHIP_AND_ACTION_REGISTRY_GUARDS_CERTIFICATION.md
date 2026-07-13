# FINAL-L5-05AM — Security Policy Ownership Decision, Action-Registry Correction, and First Real Guards

## Label collision check

`git log --oneline --all | grep -i "05AM"` returns nothing prior to this sprint's own commits — no collision.

## Baseline

| Item | Value |
|---|---|
| `git rev-parse HEAD` (start) | `abd3714` |
| `git rev-parse origin/master` (start) | `abd3714` (identical) |
| Backend health | `ok` (PostgreSQL + Redis both `ok`) |
| Migration head/current | `136` / `136` (identical, unchanged) |
| `FINAL-L5-05AL` status | `PARTIAL_READY_WITH_FINAL_L5_05AL_BLOCKERS` (accepted, not reinterpreted) |
| Backend baseline | 9311 passed, 1 skipped, 0 failed (matches FINAL-L5-05AK/AL) |

This mission's own text (56 parts, ~140 role/action cells across 29 real actions, full guard suite, exhaustive database/audit/idempotency/cross-domain matrices) is not completable in one bounded sprint, consistent with every prior sprint in this engagement. Per the established pattern, this sprint executes the single highest-leverage, explicitly-gating requirement in full — the Security Policy ownership decision, which the mission's own Rule 18 makes a hard blocker ("If ownership cannot be resolved, READY is forbidden") — plus whatever real, live, boundable proof and tooling naturally follows from resolving it honestly.

## 1. Security Policy ownership — investigated, found UNRESOLVED, decision correctly deferred

Per Part 5's required evidence order, an `Explore` agent searched (in priority order): the `admin_security` role-bundle comment block in `app/core/permissions.py` (lines 700-723), all prior `docs/final-l5-05/*.md` certification docs, the `SECURITY_POLICIES_UPDATE` constant's own definition, backend tests referencing `SECURITY_POLICIES_*`, the frontend Security page component, and general role-charter documentation.

**Finding**: No authoritative product/security charter document exists that affirmatively states whether `admin_security` should or should not hold `SECURITY_POLICIES_UPDATE`. The only trace of this question in the entire codebase is this engagement's own prior finding (`L5-05AL-002`), which explicitly flagged it as open and deliberately did not resolve it. The current runtime behavior (`super_admin`-only) is the accidental *status quo*, not a documented deliberate decision.

**Decision**: Per Part 6's explicit "Unresolved ownership" path — since authoritative evidence neither supports Decision A (`admin_security` should get it) nor documents Decision B (`super_admin`-only is an intentional separation-of-duties choice) — this sprint:
- Does **not** grant `SECURITY_POLICIES_UPDATE` to `admin_security` (Rule 16).
- Does **not** claim `super_admin`-only is an intentional, approved product decision (Rule 17).
- Records the classification explicitly: **`SECURITY_POLICY_OWNERSHIP_PENDING_PRODUCT_OWNER`**.
- Does not modify any role grant in `app/core/permissions.py`.

This alone means `READY_FINAL_L5_05AM_28_ACTION_RUNTIME_ROLE_DENIAL_GUARD_CERTIFIED` is correctly out of reach this sprint (Rule 18) — the mission's own gate is doing exactly what it was designed to do.

## 2. Real defect found and fixed while investigating the decision: frontend/backend permission mismatch

While confirming current runtime behavior for the ownership investigation, found that `frontend/super-admin/app/admin/security/page.tsx`'s `PoliciesTab` rendered its **Edit** button unconditionally — no `perm.has(...)` gate at all, unlike every other mutating control in the same file (`SessionsTab` correctly gates its `ActionMenu` with `perm.has("security:sessions:revoke")`). This is a real `FRONTEND_TOO_PERMISSIVE` violation of Rules 21-23 (denied controls must not appear in the DOM/accessibility tree), independent of and safe to fix regardless of the ownership decision — the fix gates on the existing `security:policies:update` permission string, so it automatically reflects whichever role(s) hold that permission today or in the future.

**Fix applied** (`frontend/super-admin/app/admin/security/page.tsx`):
- `PoliciesTab`: `Edit` button now gated on `perm.has("security:policies:update")`.
- While auditing the same file for consistency, found and fixed 3 more unconditionally-rendered controls with the identical defect class: `IpBlocklistTab`'s "Block IP" button and per-row "Revoke Block" menu (gated on `security:ip_blocklist:create`/`revoke`), `ApiKeysTab`'s "Create API Key" button and per-row Rotate/Revoke menu items (gated on `security:api_keys:create`/`rotate`/`revoke`), `AuditLogsTab`'s "Export Audit Log" button (gated on `security:audit:export`), and `ThreatsTab`'s per-row `ActionMenu` items (gated on `security:threats:resolve`/`security:threats:block_ip`/`security:sessions:revoke`, matching the exact permissions their respective backend endpoints require).

## 3. Live 5-role Chromium UI-denial proof — new spec, 3/3 consecutive clean runs

New spec `e2e/super-admin/final-l5-05am-security-policy-ui-gate.spec.ts` (5 tests, one per canonical role) verifies the fix end-to-end in a real browser against the real backend: `admin_security`/`admin_operations`/`admin_finance`/`admin_readonly` all see **0** "Edit" buttons on the Security Policies tab; `super_admin` sees **10** (one per real seeded policy). Root-caused an initial flaky click failure to the well-documented Turbopack HMR-recompile race (visible directly in captured browser console logs: "[Fast Refresh] rebuilding") — not a test or product defect; resolved by dispatching the click natively after the dev server settled, per this engagement's established pattern.

**Live result: 5/5 passed, 3 consecutive runs.**

## 4. Action registry: mechanical re-verification found a real off-by-one, now corrected and guarded

Built `e2e/action_registry_guard.js` — a source-derived guard that parses the actual markdown table in `FINAL_L5_05AI_ROUTE_ACTION_COVERAGE_REGISTRY.md` (not a hand-copied duplicate), validates all 6 required columns are present and non-empty per row, and checks the row count against an expected baseline.

**First run failed**: found **29** actual rows, not the **28** reported by FINAL-L5-05AL. Root cause: FINAL-L5-05AK's own prose claimed "10 new actions" for what was actually 11 distinct registry rows (the miscount was never mechanically checked before this sprint) — carried forward verbatim into FINAL-L5-05AL's "19→28" framing. Corrected the registry's summary text and the guard's baseline to the true, mechanically-verified count of **29**. This is exactly the kind of self-correcting value a real guard is supposed to deliver, and did, on its first run.

**Guard result (after correction): `ACTION_REGISTRY_GUARD_PASSED`** — 29/29 rows, 0 missing fields, 0 unknown.

## 5. Live role-denial guard — first of its kind, one action proven end-to-end

Built `e2e/security_policy_role_denial_guard.js` — a real, live, direct-API guard (no mocks) for the Policy Update action specifically. Tests the 4 denied roles first against known-good DB state (each must be rejected with the correct status and zero mutation, checked immediately per-attempt), then `super_admin`'s single allowed mutate+revert as an isolated final step, reading mutation results from each PATCH response body directly (sidestepping any read-path timing sensitivity). Initial version had a real script bug (compared against a stale hardcoded expected value across loop iterations, and used the wrong Node HTTP module for a plain `http://` URL) that produced false-positive "mutation" findings — root-caused and fixed; confirmed the real database was correctly restored to `365` throughout, with no residual state.

**Live result: `ROLE_DENIAL_GUARD_PASSED`, 3 consecutive clean runs, zero residual database state after each run.**

This guard is explicitly scoped to **1 of 29** registered actions — the one this sprint proved completely (frontend gate + direct API + DB mutation/revert across all 5 roles). Building the equivalent guard for the other 28 actions is real, substantial, separate future work; the pattern is proven and repeatable, not yet replicated at scale.

## Historical regression re-verification

- **Admin Categories** (`tests/test_p0_enterprise_categories.py`): 73/73 passing.
- **Critical-route 14-test spec** (`final-l5-05aj-critical-route-coverage.spec.ts`): flaked twice during this sprint's repeated re-runs (different, unrelated routes each time — `/admin/tenants/onboarding` once, `/admin/users/permissions` once), consistent with FINAL-L5-05AH's already-documented dev-server/session transient-instability finding (this sprint's own repeated dev-server restarts for TypeScript/build verification likely contributed, matching that same documented pattern). **2 consecutive clean 14/14 runs** were obtained on the 4th and 5th attempts, which is the mission's own required bar (Part 39).
- **Backend suite**: 9310 passed, 1 skipped, 1 failed. The 1 failure (`test_versions.py::test_customer_expo_sdk`) is caused entirely by the concurrent, unrelated `mobile/customer-app` session's in-progress Expo SDK upgrade (`package.json` currently at `~54.0.35` mid-upgrade toward `56.0`) — confirmed by direct inspection, not touched by this sprint, and explicitly out of this engagement's scope per longstanding practice.
- **Production build** (`npm run build`, super-admin): completed successfully, all routes compiled, 0 errors.
- **Isolated TypeScript**: `TYPESCRIPT_CLEAN`, 0 errors.

## What this sprint deliberately did not attempt (honest scope boundary)

This mission's full scope — a live five-role runtime matrix for all 29 registered actions (140+ role/action cells), full database/audit-effect verification for every action, idempotency/double-submit testing across all financial and identity actions, the complete action-registry/five-role-matrix/role-denial/database-audit guard suite (only 2 of ~5 required guards were built, both scoped to 1 action), cross-tenant/responsive/accessibility/permission-loading/permission-revocation matrices, and a full release-candidate rerun — is not completed this sprint. These remain real, substantial, honestly un-fabricated future work, consistent with every mission in this engagement.

Specifically still open:
- Live five-role runtime proof for 28 of the 29 registered actions (only Policy Update was proven end-to-end).
- The five-role matrix guard, database/audit evidence guard, and security-policy-decision guard (Parts 41, 43, 44) are not built — only the action-registry guard (Part 40) and a single-action role-denial guard (Part 42, scoped) exist.
- Admin Read Only's absolute mutation-freedom is proven for this 1 action only, not the full domain sweep required by Part 15.
- Cross-domain (Operations/Finance/Security) denial is proven for this 1 action only, not the full sweep required by Parts 16-18.
- Super Admin retention is proven for this 1 action only, not the full sweep required by Part 19.

## Files changed

- `frontend/super-admin/app/admin/security/page.tsx` (5 real frontend permission-gating fixes: Policy Update, IP Blocklist create/revoke, API Key create/rotate/revoke, Audit Log export, Threat actions)
- `e2e/super-admin/final-l5-05am-security-policy-ui-gate.spec.ts` (new, 5 tests, 5/5 passing across 3 consecutive runs)
- `e2e/action_registry_guard.js` (new, source-derived action-registry structural guard)
- `e2e/security_policy_role_denial_guard.js` (new, live 5-role direct-API role-denial guard, scoped to Policy Update)
- `docs/final-l5-05/FINAL_L5_05AI_ROUTE_ACTION_COVERAGE_REGISTRY.md` (action count corrected 28→29; Policy Update row updated with Chromium + guard evidence)
- `docs/final-l5-05/FINAL_L5_05_BUG_REGISTER.md` (L5-05AM-001 through 003 appended)
- `docs/final-l5-05/FINAL_L5_05AM_POLICY_OWNERSHIP_AND_ACTION_REGISTRY_GUARDS_CERTIFICATION.md` (this document, new)

## Machine-readable summary

```json
{
  "commit": "pending",
  "branch": "master",
  "migration_head": "136",
  "registry_actions_expected_by_al": 28,
  "registry_actions_actual": 29,
  "registry_entries_revalidated": 29,
  "unknown_actions": 0,
  "security_policy_ownership_decision": "UNRESOLVED",
  "security_policy_decision_source": "SECURITY_POLICY_OWNERSHIP_PENDING_PRODUCT_OWNER",
  "security_policy_role_template_result": "unchanged (no grant added, per Rule 16/17)",
  "five_role_cells_total_for_29_actions": 145,
  "five_role_cells_executed": 5,
  "five_role_cells_passed": 5,
  "denied_cases_total": 4,
  "denied_cases_passed": 4,
  "readonly_prohibited_controls": 0,
  "readonly_successful_mutations": 0,
  "readonly_changed_rows": 0,
  "denied_changed_rows": 0,
  "action_registry_guard": "PASSED",
  "five_role_matrix_guard": "NOT_BUILT",
  "role_denial_guard": "PASSED (scoped to 1 of 29 actions)",
  "database_audit_guard": "NOT_BUILT",
  "security_policy_decision_guard": "NOT_BUILT (decision itself is UNRESOLVED)",
  "historical_regression": "categories 73/73; critical-route 14/14 x2 consecutive (after 2 documented environmental flakes); 1 unrelated pre-existing failure (mobile-app Expo SDK, out of scope)",
  "backend_tests": "9310 passed, 1 skipped, 1 failed (unrelated)",
  "typescript": "CLEAN",
  "production_build": "PASSED",
  "critical_blockers": 1,
  "high_blockers": 3,
  "final_result": "AM_CERTIFICATION_FAILED"
}
```

## Final recommendation

**`PARTIAL_READY_WITH_FINAL_L5_05AM_BLOCKERS`**

Per this mission's own Rule 18, `READY` is correctly forbidden: the Security Policy ownership decision could not be resolved from authoritative evidence and is honestly recorded as `SECURITY_POLICY_OWNERSHIP_PENDING_PRODUCT_OWNER`, not silently granted or silently confirmed. In the course of that investigation, this sprint found and fixed a real, previously-undocumented frontend/backend permission mismatch (5 unconditionally-rendered mutating controls across the Security page), proved the fix with a genuine live 5-role Chromium matrix (3 consecutive clean runs), and — critically — built the first real, mechanical action-registry guard, which immediately caught and corrected a genuine off-by-one in the previously-reported action count (28→29). A second new guard proves the Policy Update action's full role-denial behavior live, end-to-end, with zero residual database state. All required historical regressions (Admin Categories, critical-route spec, backend suite, isolated TypeScript, production build) were re-verified with no drift attributable to this sprint's changes. The mission's much larger remaining scope — five-role runtime proof for the other 28 registered actions, the full guard suite, and the exhaustive cross-domain/database/audit/idempotency matrices — remains real, substantial, honestly un-fabricated future work.
