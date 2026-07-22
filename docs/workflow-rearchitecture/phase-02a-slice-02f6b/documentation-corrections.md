# Documentation Corrections — Workstream 9

## Corrections applied to Slice 2F-6A documentation

### `docs/workflow-rearchitecture/phase-02a-slice-02f6a/technician-persona-decision.md`
Replaced the ambiguous label **"STAFF_ONLY"** (used 3 times, for
`provider_record_payment`, `staff_create_invoice`, `staff_add_invoice_item`)
with the precise **"TENANT_OWNER_OR_CANONICAL_STAFF"**. The underlying
guard (`require_owner_or_office_staff_mutation`, admitting
`{super_admin, tenant_owner, staff}`, excluding `technician`) was always
correct — only the prose label was corrected, since "STAFF_ONLY" could
be misread as excluding `tenant_owner`.

### `docs/workflow-rearchitecture/phase-02a-slice-02f6a/known-limitations.md`
Corrected the same "STAFF_ONLY" reference in item 7 to
"TENANT_OWNER_OR_CANONICAL_STAFF."

## Files already correct (verified, not changed)
`invoice-payment-final-policy-matrix.csv` already used the precise dual-
persona classification (`TENANT_OWNER_RECORD_PAYMENT + DELEGATED_STAFF_RECORD_PAYMENT`,
etc.) and listed `tenant_owner + staff` in the `acting_role_admitted`
column — no correction needed there.

## Final, authoritative persona wording (per this slice's mission)
- **Issue invoice**: `TENANT_OWNER_ONLY`.
- **Create invoice**: `TENANT_OWNER_OR_CANONICAL_STAFF`.
- **Add invoice item**: `TENANT_OWNER_OR_CANONICAL_STAFF`.
- **Record on-site payment**: `TENANT_OWNER_OR_CANONICAL_STAFF`.
- **Technician**: denied for all four.
- Mutation-capable access scope required for every allowed persona.

## Approval status update
Slice 2F-6A's `approval-gate.md` status
(`SECURITY_AND_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED`) is **not
downgraded** by this correction — the backend guard implementation was
always correct; only the prose label in 2 files was imprecise. This
slice's own `approval-gate.md` reports the frontend-alignment status
separately, per the mission's instruction to "update the approval status
only after frontend alignment is proven."
