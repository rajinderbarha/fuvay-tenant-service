# Known Limitations — Slice 2F-20

1. **Export worker absent.** `generate_export` queues a `"processing"`
   `ComplianceExport` with no code path anywhere that ever produces a
   `"ready"` export. Confirmed by exhaustive search (Celery, RQ, Arq,
   Dramatiq, `BackgroundTasks`, event-bus consumers, cron jobs, file
   generation, storage writes, signed URLs) — see
   `compliance-export-worker-discovery.md`. This is the reason final
   status is `DOMAIN_INTEGRITY_BLOCKED`, not the reason security status
   is blocked.

2. **Export duplication defect.** No dedup/idempotency check exists on
   `generate_export`; repeated calls, or a race with the admin
   `process_request` path, create multiple independent, permanently-stuck
   export rows for the same request. Not fixed this slice — see
   `product-decisions-required.md` item 2.

3. **`ComplianceRequest`/`ComplianceExport` lack a schema-level
   `tenant_id` column.** Tenant scoping exists only via
   `metadata_json["tenant_id"]`/`["related_tenant_id"]`, an unindexed
   JSONB mechanism. This slice made the field server-owned and
   atomically written (closing the security gap) but did NOT add a
   migration or redesign the schema, per explicit mission prohibition.
   The structural gap itself remains — a schema migration (out of scope
   this slice) would be the durable long-term fix.

4. **Duplicate audit-log call in `download_export`.** Found, not fixed —
   see `product-decisions-required.md` item 5.

5. **Un-consolidated validation constant sets.** `enterprise_service.py`'s
   `VALID_SUBJECT_TYPES`/`VALID_REQUEST_TYPES` and
   `provider_router.py`'s `TENANT_ALLOWED_REQUEST_TYPES` are maintained
   independently; this slice widened the former to match the latter but
   did not unify them. Future drift is possible if either is edited in
   isolation again.

6. **Frontend/mobile caller audit deferred.** Investigation of live
   frontend/mobile callers of these 6 routes was not completed to a
   conclusive finding within this slice's time budget — see
   `frontend-mobile-caller-audit.md`, labeled
   `FRONTEND_CALLER_AUDIT_DEFERRED` (distinct from a confirmed-absent
   surface). No frontend code was modified this slice regardless, so this
   does not affect the backend authorization closure, but it means no
   claim is made about live caller compatibility with the
   `require_tenant_owner_mutation` swap (behaviorally identical role
   admission to the prior `require_tenant_owner`, so compatibility risk
   is assessed as low, not zero).

7. **`staff` role never admitted.** Consistent with pre-existing
   behavior, not a regression — see `product-decisions-required.md`
   item 3.
