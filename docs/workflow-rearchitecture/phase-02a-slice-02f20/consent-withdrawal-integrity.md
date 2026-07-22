# Consent Withdrawal Integrity

## Trace (post-fix)
1. Route: `POST /v1/provider/compliance/consents/{consent_type}/withdraw`.
2. Acting persona: `tenant_owner`/`super_admin`, now access-scope-aware
   (`require_tenant_owner_mutation`, this slice).
3. Subject identity: `actor_id = uuid.UUID(u.user_id)` — the caller's own
   identity; consent is always self-withdrawn by the tenant owner acting
   for their own account, never for an arbitrary other user.
4. Tenant source: `tenant_id_str = _require_tenant(u)` → now forwarded as
   `uuid.UUID(tenant_id_str)` into `s.revoke_consent(..., tenant_id=...)`
   (THIS SLICE — was always `None` before).
5. Request schema: raw JSON, only `reason` read.
6. Service call: `ComplianceEnterpriseService.revoke_consent(actor_id,
   consent_type, reason, tenant_id=tenant_id)` → `ComplianceService.withdraw_consent(user_id,
   tenant_id, consent_type, "1.0")` → `record_consent(...)`.
7. **Previous `tenant_id=None` behavior**: every `ConsentRecord` written
   through this path had `tenant_id = NULL` in the database, regardless
   of which tenant's owner withdrew it — a regulatory-record attribution
   defect (DPDP consent records should be traceable to the tenant
   relationship they concern).
8. Consent record lookup: NONE — `withdraw_consent`/`record_consent`
   always INSERTS a new `ConsentRecord` row with `action=WITHDRAWN`; there
   is no "find existing consent, verify its tenant, then update" step.
   This means consent withdrawal is **append-only history**, not a
   single-row toggle — repeated withdrawal of the same `consent_type`
   simply appends another `WITHDRAWN` row (idempotency is at the
   "current effective state" query level elsewhere in the service, not at
   write time — unchanged, not investigated further this slice since it's
   pre-existing, correct-by-design append-only audit behavior).
9. Consent category/purpose: `consent_type`, validated against
   `TENANT_WITHDRAWABLE_CONSENT_TYPES` (unchanged, preserved) — one
   purpose cannot silently alter another since `consent_type` is a
   required, allowlist-validated path parameter, not inferred.
10. Resulting state: `ConsentAction.WITHDRAWN`, `withdrawn_at=now()`.
11. History/audit event: `ComplianceAuditLog` insert with action
    `"consent.admin_revoked"` (a slightly misleading action name for a
    TENANT-initiated withdrawal, inherited unchanged from
    `enterprise_service.revoke_consent` — flagged in
    `known-limitations.md`, not renamed this slice to avoid unrelated
    behavior/string changes).
12. Downstream processing effect / notification effect: NONE — confirmed,
    no cascading deletion, no notification is triggered by consent
    withdrawal in this codebase.
13. Export/deletion interaction: NONE — withdrawing consent does NOT
    automatically trigger data deletion or export; confirmed by code read,
    consistent with the mission's explicit instruction not to assume this
    behavior exists.
14. Commit ordering: `_audit(...)` then `await db.commit()` — the
    `ConsentRecord` insert (inside `revoke_consent`) and the
    `ComplianceAuditLog` insert (in the router) share the SAME
    transaction/commit.

## Requirements checklist
- **`tenant_id` never passed as `None` when tenant scope is required** —
  FIXED for the tenant-owner (provider) path; customer/admin paths
  correctly continue to pass `None` where no tenant scope legitimately
  applies.
- **Tenant identity server-derived** — TRUE, unchanged.
- **Consent record belongs to the exact tenant and subject** — TRUE now
  for tenant attribution (fixed); subject attribution (`user_id`) was
  already always correct (self-scoped, no request_id to spoof).
- **Provider cannot withdraw consent for an unrelated subject** — TRUE,
  structurally (no subject-identifier input field exists on this route at
  all).
- **One consent purpose cannot silently alter another** — TRUE
  (`consent_type` is an explicit, validated path parameter).
- **Repeated withdrawal behavior explicit** — TRUE: append-only history,
  each call creates a new `WITHDRAWN` row (documented above, not changed).
- **Withdrawal actor is the real caller** — TRUE, unchanged
  (`actor_id = uuid.UUID(u.user_id)`).
- **Provider-administered withdrawal remains distinguishable from customer
  self-service in audit history where the model supports it** — PARTIALLY:
  `ComplianceAuditLog.actor_role` records `u.role` (`"tenant_owner"` vs.
  `"customer"`), which DOES distinguish the two in the audit trail: this
  was already true before this slice (not a new fix, re-confirmed).
- **Invalid withdrawal creates no partial record or success event** —
  TRUE: `consent_type` validation (allowlist check) and rate-limiting both
  raise BEFORE the service call — proven by
  `no-partial-persistence-side-effect-proof.md`.
