# Duplicate and Concurrency Integrity — Workstream 9

| Operation | Classification | Evidence |
|---|---|---|
| Duplicate service enablement (`enable_service` twice for the same `master_service_id`) | **DUPLICATE_REJECTED** | `TENANT_SERVICE_ALREADY_ENABLED` (409), pre-existing, unmodified. Also backed by the schema-level `uq_ts_tenant_service` unique constraint. |
| Re-enabling a previously-disabled service | **IDEMPOTENT** | `enable_service`'s "re-enable" path flips `is_enabled` back to `True` on the existing row rather than creating a duplicate — pre-existing, unmodified. |
| Duplicate `disable_service` (disabling an already-disabled service) | **DUPLICATE_REJECTED** (effectively) | `disable_service` raises `TENANT_SERVICE_NOT_ENABLED` (404) if no row with `tenant_id`+`master_service_id` is found — but note: the query does **not** filter on `is_enabled`, so a request to disable an already-disabled service finds the existing row and re-sets `is_enabled = False` (already false) — an idempotent no-op, not a rejection. Classified here as effectively idempotent for the "already disabled" case, and duplicate-rejected only in the sense that a truly nonexistent mapping is rejected. |
| Concurrent `enable_service` requests for the same tenant+service | **CONCURRENCY_RISK_DOCUMENTED** | No row lock or advisory lock exists in `enable_service` (unlike `serviceability.create_service_area`'s `pg_advisory_xact_lock`, Slice 2F-7). Two simultaneous first-time enable requests could theoretically both pass the "not already enabled" check before either commits, given no unique-constraint pre-check locking. The schema-level `uq_ts_tenant_service` unique constraint would still prevent a literal duplicate row at the database level (the loser's `INSERT` would fail with an `IntegrityError`), but that failure is not gracefully caught in application code as a clean 409 — it would surface as a raw database exception. Not fixed this slice: no direct evidence (test or incident report) proves this has occurred in production, and closing it correctly would require either adding an advisory lock (mirroring serviceability's own pattern) or an `ON CONFLICT` upsert — a reasonable candidate for a future slice, not conclusively required by this one's evidence bar. |
| Concurrent `disable_service` requests | **CONCURRENCY_RISK_DOCUMENTED** (lower severity) | Both would independently set `is_enabled = False` — the final state is correct regardless of ordering (no duplicate-row risk since no new row is created). |
| Bulk enable/disable | **N/A** | No bulk endpoint exists in this router. |
| Type/brand mapping duplicate protection | **DUPLICATE_ALLOWED / not independently re-verified** | `set_tenant_service_types`/`set_tenant_service_brands` appear (from their names and signature) to *replace* the full set of `type_ids`/`brand_ids` per call, not incrementally add one at a time — meaning "duplicate" in the traditional sense may not apply the same way; this was not exhaustively re-traced line-by-line this slice, as no defect was evidenced. |

## Conclusion
No conclusively-proven, unfixed integrity defect was found in duplicate
handling. One concurrency risk (unlocked `enable_service` insert path)
is documented, matching the same category of pre-existing, platform-wide
lockless pattern already documented in Slice 2F-7 for
`match_tenants_for_location`'s callers generally — not redesigned or
fixed here, since the schema-level unique constraint already provides a
hard backstop against an actual duplicate row, even if the error surface
is not as clean as it could be.
