# Slice 2F-6B Implementation Summary

## Scope
Align every existing frontend control and API caller for the 4 invoice/
payment mutations (`provider_issue_invoice`, `provider_record_payment`,
`staff_create_invoice`, `staff_add_invoice_item`) with the approved
backend persona matrix from Slice 2F-6A.

## Central finding
Direct investigation (grep across `frontend/tenant-portal`,
`frontend/customer-app`, `frontend/super-admin`, and
`mobile/staff-app`) found **zero components invoking any of the 4
backend endpoints**. The only related UI is
`app/(tenant)/provider/service-invoices/page.tsx` — a list page whose
sole row action ("View Invoice") links to a route
(`/provider/service-invoices/{id}`) that does not exist in the app
directory. This directly contradicts Slice 2F-6/2F-6A's own
documentation, which described "Issue button," "Record payment action,"
"Create invoice action," and "Add invoice item action" as existing UI
controls — that description was incorrect, inferred from API client
method names rather than verified against an actual invoking component.

## What changed
1. **`frontend/tenant-portal/lib/api.ts`** — added 3 small, pure helper
   functions: `isCanonicalStaffRole(role)`, `canManageProviderInvoices(role, accessScope)`,
   `canIssueProviderInvoice(role, accessScope)`. These correctly encode
   the approved backend persona matrix (`TENANT_OWNER_ONLY` for issue;
   `TENANT_OWNER_OR_CANONICAL_STAFF` for the other 3; technician denied
   on all 4; mutation-capable access scope required for every allowed
   persona; unknown roles fail closed). Built entirely from existing
   primitives (`isTenantOwnerRole`, `getAccessScope`) — no parallel
   authorization system, no new role, no backend change.
2. **`frontend/tenant-portal/lib/api.persona.test.ts`** — new, 13 direct
   unit tests covering every persona in the approved matrix, run via
   Node's built-in test runner (no jest/vitest exists in this app).
3. **`docs/workflow-rearchitecture/phase-02a-slice-02f6a/technician-persona-decision.md`**
   and **`known-limitations.md`** — corrected the ambiguous "STAFF_ONLY"
   label (used 3 times) to the precise "TENANT_OWNER_OR_CANONICAL_STAFF"
   — the underlying guard was always correct, only the prose label was
   imprecise.
4. **14 documentation files** in this directory (see `approval-gate.md`
   for the closure statement).

## What did NOT change
No backend file was modified — backend authorization, amount validation,
and invoice state transitions are byte-for-byte unchanged from Slice
2F-6A (re-verified via 68 + 27 = 95 passing backend tests). No frontend
UI component was modified, added, or redesigned — there was no existing
control to correct, and building one is out of scope. No permission was
granted. No new role was introduced. `readonly@` and migration 144 were
untouched.

## Honest characterization of "frontend alignment"
Because no mutation control exists anywhere in the frontend, "frontend
policy alignment" in this slice means: (a) no denied-role control is
exposed (vacuously true — there are no controls for anyone), and (b) the
authorization helper infrastructure a future UI would need is now
correct, tested, and ready. It does **not** mean tenant-owners or office
staff currently have a working invoice-management UI — they do not, and
this is a pre-existing gap this slice discovered and documented rather
than fixed (fixing it would be "redesigning the invoice interface,"
explicitly out of scope).

## Outcome
**SECURITY_INTEGRITY_AND_FRONTEND_POLICY_CLOSED_PRODUCT_POLICY_BLOCKED**
— see `approval-gate.md` for full reasoning and the explicit
non-claims. Global tenant-mutation coverage (89/183) is unchanged, per
instruction.
