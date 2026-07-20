# Deferred Items — Slice 2F-20

Items explicitly identified but not actioned this slice, with reason and
suggested owner for follow-up.

| Item | Reason deferred | Suggested next step |
|---|---|---|
| Export-generation worker build | Requires new infrastructure (file gen, storage, signed URLs) — disproportionate to an authorization-focused slice; mission explicitly forbade fabricating one | Dedicated future slice/product decision — see `product-decisions-required.md` #1 |
| Export deduplication check | Would protect a worker that doesn't exist yet; not meaningfully useful in isolation | Build alongside the worker |
| `ComplianceRequest`/`ComplianceExport` schema-level `tenant_id` migration | Explicitly prohibited this slice (no migration permitted) | Future slice with migration authority |
| Duplicate `_audit()` call in `download_export` | Cosmetic/log-volume, not security-relevant | Small cleanup slice or opportunistic fix |
| Consolidation of subject-type/request-type constant sets | Out of proportion to this slice's authorization focus; only the minimal fix needed to unblock `create_my_request` was made | Future refactor slice |
| Frontend/mobile caller audit for these 6 routes | Not completed to a conclusive finding within this slice's time budget | Follow-up investigation; low compatibility risk since role admission is behaviorally unchanged |
| `staff` role admission policy for compliance routes | Product/policy decision, not an implementation task | Product decision — see `product-decisions-required.md` #3 |

No other module was begun. The remaining 9 non-selected modules (20
routes) are unchanged from the 2F-19 queue — see
`remaining-module-queue-update.csv`.
