# Six-Defect Remediation Report — Slice 2F-39A2R

All six defects Slice 2F-39A2 found and deliberately did not force-fix
are now **RESOLVED**. Each entry below states the required fields.

---

## 1. `POST /v1/security/activity/record` (`record_activity`)

- **Final mutation category:** `CANONICAL_TENANT_PROVIDER_MUTATION` (once fixed)
- **Mounted/externally callable:** Yes, mounted, reachable by any authenticated user
- **Authentication (before/after):** `get_current_user` — unchanged
- **Permission (before/after):** None — unchanged (no permission requirement documented anywhere for this route; not invented this slice)
- **Access scope (before/after):** None — unchanged
- **Client-controlled identifiers (before):** `tenant_id`, `entity_id`, `entity_type`, `activity_type` all from request body
- **Tenant/ownership derivation (before → after):** `tenant_id` trusted verbatim from body → now cross-checked against `self.actor_tenant_id` via `_require_trusted_tenant` (super_admin exempt)
- **Intended caller model:** End-user-facing HTTP route (confirmed: zero internal callers found anywhere in the codebase; documented as a genuine authenticated-principal-reachable gap since Slice 2F-26D)
- **Disposition:** **RESOLVED** (was `UNRESOLVED_AUTHORIZATION_DEFECT`)
- **Evidence:** `TestRecordActivityTenantScoping` (2 tests)

## 2. `POST /v1/security/audit-log` (`write_audit_entry`)

- **Final mutation category:** `CANONICAL_TENANT_PROVIDER_MUTATION` (once fixed)
- **Mounted/externally callable:** Yes
- **Authentication:** `get_current_user` — unchanged
- **Permission:** None — unchanged
- **Access scope:** None — unchanged
- **Client-controlled identifiers (before):** `tenant_id`, `entity_id`, `operation`, `before`/`after` all from body
- **Tenant/ownership derivation (before → after):** trusted verbatim → cross-checked via `_require_trusted_tenant`
- **Intended caller model:** End-user-facing; documented since Slice 2F-26D ("any authenticated principal may append arbitrary audit entries attributed to another tenant, weakening every control that cites the audit log as evidence")
- **Disposition:** **RESOLVED**
- **Evidence:** `TestWriteAuditEntryTenantScoping` (2 tests)

## 3. `POST /v1/security/sessions` (`create_session`)

- **Final mutation category:** `CANONICAL_TENANT_PROVIDER_MUTATION` (once fixed)
- **Mounted/externally callable:** Yes
- **Authentication:** `get_current_user` — unchanged
- **Permission:** None — unchanged
- **Access scope:** None — unchanged
- **Client-controlled identifiers (before):** `user_id`, `tenant_id`, `session_id` all from body
- **Tenant/ownership derivation (before → after):** `user_id` trusted verbatim → must equal `self.actor_id` (super_admin exempt); `tenant_id` cross-checked via `_require_trusted_tenant`
- **Intended caller model:** End-user-facing (not independently documented in the 2F-26 corpus, but structurally identical to the other three and with zero internal callers found — treated the same way)
- **Disposition:** **RESOLVED**
- **Evidence:** `TestCreateSessionActorScoping` (2 tests)

## 4. `DELETE /v1/security/sessions/{session_id}` (`revoke_session`) — HIGH severity

- **Final mutation category:** `CANONICAL_TENANT_PROVIDER_MUTATION` (once fixed)
- **Mounted/externally callable:** Yes
- **Authentication:** `get_current_user` — unchanged
- **Permission:** None — unchanged
- **Access scope:** None — unchanged
- **Client-controlled identifiers (before):** `session_id` (path) — "the principal is never referenced" (Slice 2F-26D's own words)
- **Tenant/ownership derivation (before → after):** none at all → session's `user_id` now compared to `self.actor_id` (super_admin exempt); a foreign session is treated identically to a missing one (non-oracular)
- **Intended caller model:** End-user-facing; documented since Slice 2F-26D as the single highest-signal item in that entire observation corpus, HIGH severity
- **Disposition:** **RESOLVED**
- **Evidence:** `TestRevokeSessionOwnership` (3 tests, including a super_admin-exemption case)
- **Secondary fix:** `test_phase12.py::test_revoke_session_deletes_redis_first` updated (`PROTECTED_BY_LATER_SLICE`) — the pre-fix design intentionally deleted Redis before any check; the fix necessarily adds a read-only ownership lookup before the delete, while preserving the original immediacy guarantee for the DB *write*.

## 5. `POST /v1/pricing/tenants/{tenant_id}/rules/{rule_id}/activate` (`activate_rule`)

- **Final mutation category:** `CANONICAL_TENANT_PROVIDER_MUTATION` (already counted toward the denominator by 2F-39A2, now actually protected)
- **Mounted/externally callable:** Yes
- **Authentication (before/after):** `require_permission(P.TENANT_UPDATE)` → `require_tenant_mutation_permission(P.TENANT_UPDATE)`
- **Permission:** `P.TENANT_UPDATE` — unchanged
- **Access scope (before/after):** not enforced → now enforced (the `require_tenant_mutation_permission` wrapper's read-only-scope rejection)
- **Client-controlled identifiers (before):** `rule_id` only — **`tenant_id` was accepted by the router but never even passed to the service call at all**
- **Tenant/ownership derivation (before → after):** **zero tenant scoping whatsoever** → `tenant_id` now passed through, cross-checked via `_require_trusted_tenant`, and the fetched rule's `tenant_id` compared against it (`NotFoundException` on mismatch, matching `update_rule`/`delete_rule`'s established pattern)
- **Intended caller model:** Tenant-side mutation (unambiguous — sibling routes `update_rule`/`delete_rule` in the same router already establish this)
- **Disposition:** **RESOLVED**
- **Evidence:** `TestPricingRuleActivationTenantScoping` (4 tests)
- **Note:** this was actually worse than the "guard mismatch" class 2F-39A2 originally described — it was a complete absence of tenant scoping, not merely a read-only-scope bypass.

## 6. `PATCH /v1/pricing/tenants/{tenant_id}/rules/{rule_id}/deactivate` (`deactivate_rule`)

Identical finding and fix to #5 above.

- **Disposition:** **RESOLVED**

---

## Numerator/denominator impact

`activate_rule`/`deactivate_rule` were already counted in 2F-39A2's 321+
denominator as `CANONICAL_TENANT_PROVIDER_MUTATION`, but were **not
actually protected** until this slice. Per the review's own instruction:
"the cumulative report cannot claim zero canonical unprotected mutations
until they are repaired." **They are now repaired** — the canonical
denominator's "0 unprotected" claim is restored to being true for these
two routes, not merely asserted.

The 4 `security.router` findings are not part of the canonical
tenant/provider denominator (they were classified
`PRODUCT_DECISION_REQUIRED`, not `CANONICAL_TENANT_PROVIDER_MUTATION`,
in 2F-39A2's own census) — they are now reclassified
`CANONICAL_TENANT_PROVIDER_MUTATION` in `final-route-classification.csv`'s
successor entry for this slice, since the intended-caller-model question
is now resolved (end-user-facing, tenant-scoped) and they are protected.
