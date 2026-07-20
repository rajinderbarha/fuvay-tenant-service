# Known Limitations — Slice 2F-13

1. **Per-job checklist execution, provider verification, customer
   decisions, evidence/media, and the job-completion gate are NOT in this
   router** — they live on the out-of-scope `field_ops.service.py` /
   `field_ops.staff_router` surface (`JobChecklistItem`). This slice
   closed only the tenant checklist-TEMPLATE router. The job-execution
   surface's own authorization is a candidate for a future dedicated
   slice.
2. **`FIELD_OPS_CHECKLIST_MANAGE` default grant is tenant_owner-only** —
   staff need an explicit StaffPermission override. Not changed (product
   decision). The IDOR fix ensures a granted staff member stays
   tenant-scoped.
3. **Concurrent duplicate-template creation** relies on a SELECT-then-
   INSERT 409 guard (no unique DB constraint) — `CONCURRENCY_RISK_DOCUMENTED`,
   benign, not hardened (would need a migration, out of scope).
4. **No template versioning / publish-immutability** — templates are
   editable in place; job snapshots are copies (historical integrity
   preserved), but there is no version-pinning model.
5. **`test_module_l5_35_...::TestLive` not executed** — live-server
   dependency (`httpx.ConnectError`); pre-existing, unrelated.
6. **No frontend surface** for this router — reported absent.
