# Remediation Apply Report — Slice 2D

## One remediation was applied this slice.

### manager@demo-ac-services.local — APPLIED

Command:
```
python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
  --mapping 72640932-ef3c-4ce5-92a1-6609bff35ee0=staff \
  --disable 72640932-ef3c-4ce5-92a1-6609bff35ee0 \
  --allow 72640932-ef3c-4ce5-92a1-6609bff35ee0 \
  --reason "Slice 2D: zero usage/evidence demo account; disabling rather than granting unproven manager-shaped access (see tenant-access-model.md)" \
  --apply --confirm
```

Result: `"applied": true`, `"sessions_revoked": 0`, zero errors.

**Verified live, post-apply:**
- `users` row: `role='staff'`, `is_active=false`, `deactivated_at` set, `deactivation_reason` recorded with the exact reason string above.
- `auth_audit_logs`: one new row, `action_type='role.remediation'`, `target_id` = this user's id, `metadata` containing `previous_role='tenant_manager'`, `new_role='staff'`, `disabled=true`, `sessions_revoked=0`, `reason`, `script_version='slice-2d-v2'`.
- Full role distribution query: `tenant_manager` no longer appears anywhere in `users.role`.
- Idempotency re-check: re-running the identical command afterward correctly reports the account as no longer found among invalid-role accounts ("idempotent no-op"), confirming it does not attempt to re-apply or duplicate the change.

## One account remains explicitly NOT applied.

### readonly@demo-ac-services.local — NOT APPLIED

No mapping was submitted for this account. Per `affected-account-final-disposition.md` and `tenant-readonly-decision.md`, no canonical role can be safely assigned without either granting unintended mutation capability or requiring a broader architecture investment not in this slice's scope. This is the correct, evidence-based outcome, not an oversight.

## Net effect on the database
Before this slice: 2 invalid-role accounts (`tenant_manager` ×1, `tenant_readonly` ×1). After this slice: 1 invalid-role account (`tenant_readonly` ×1) remains, plus 1 additional `staff`-role row (the remediated, now-disabled account) — confirmed via the live role-distribution query, run both before and after.
