# Product Decisions Required — Slice 2F-6 (not resolved this slice)

## 1. Should `staff`/`technician` ever be granted `FIELD_OPS_INVOICE_GEN`?
Currently only `tenant_owner` can issue an invoice
(`provider_issue_invoice`). If the product intent is for front-desk staff
to issue invoices without owner involvement, this permission is the
natural candidate to grant to `staff`. Not granted this slice, per
"do not grant a permission merely because no role currently has it" and
because the existing evidence (permission name + owner-only grant) reads
as an intentional design choice, not an oversight.

## 2. Frontend button visibility for `provider_issue_invoice`
The tenant-portal UI does not currently hide the "Issue" button from
non-owner accounts. A staff user will now get a backend 403 instead of a
successful issue. A minimal frontend correction (hiding one button for
non-owner roles) would improve the experience but was not made this
slice (frontend redesign out of scope; backend is authoritative).

## 3. Amount validation on `record_onsite_payment`/`add_item`
No positive-value validation exists for `collected_amount`/`unit_price`/
`quantity`. Not fixed this slice (no existing in-file precedent to
mirror, unlike `package_commerce`'s `update_package`). A future slice
could add this if judged worth the design effort of choosing validation
bounds.

## 4. Per-job-assignment restriction for staff/technician
Any staff/technician within the correct tenant can act on any invoice in
that tenant — there is no restriction to "only jobs I am personally
assigned to" within this module. This may or may not be the intended
product behavior; the existing `FIELD_OPS_JOBS_CLOSE` permission grant
(to `staff`/`technician`) does not itself carry a per-assignment
restriction either, so this is consistent with the existing platform
pattern, not a new gap — flagged for awareness, not a decision this
slice needs to force.

## Recommendation (non-binding)
None of these require urgent action — the conclusively-provable defect
(missing role/permission enforcement entirely) is fixed. These are
lower-priority refinements for a future slice, should the product team
want to grant staff invoice-issuing rights or tighten payment amount
validation.
