# Product Decisions Required — Slice 2F-13

1. **Should `staff` be granted `FIELD_OPS_CHECKLIST_MANAGE` by default?**
   Currently only `tenant_owner` (+super_admin) hold it; staff need a
   StaffPermission override. This slice did not change the grant (per
   "do not add a permission / do not change role bundles"). Whether
   checklist-template administration should be a default staff capability
   is a product decision — not made here. The IDOR fix ensures that IF a
   staff member is granted it, they remain tenant-scoped.

2. **Concurrent duplicate-template creation** relies on a SELECT-then-
   INSERT 409 guard with no unique DB constraint — a benign duplicate
   risk (`CONCURRENCY_RISK_DOCUMENTED`). Adding a unique constraint would
   require a migration (out of scope). Whether to harden it is a future
   decision.

3. **Per-job checklist execution, provider verification, customer
   decisions, evidence, and the completion gate** live on the
   out-of-scope `field_ops.service.py`/`staff_router` surface
   (`JobChecklistItem`). Their authorization/ownership is a candidate for
   a future dedicated slice (`field_ops.staff_router`), explicitly not
   begun here.

4. **No template versioning / publish-immutability** exists. Whether the
   product wants versioned/immutable published templates is a future
   design decision (the mission forbids building one now).
