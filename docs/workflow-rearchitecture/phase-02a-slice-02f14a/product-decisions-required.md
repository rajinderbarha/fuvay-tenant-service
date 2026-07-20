# Product Decisions Required

1. **`JobMedia` internal/customer-visible distinction.** No `is_internal`-equivalent column
   exists (unlike `JobNote`). Any actor who can access a job at all currently sees all of its
   media. If provider-internal media (e.g. pre-repair diagnostic photos) should be hidden from
   customers, a schema change (new column + migration) is needed — explicitly not built this
   slice per the "do not build new media/upload infrastructure" instruction.
2. **`respond_to_quote`'s non-customer `customer_id` parameter.** When the caller's role is not
   `customer`, the route accepts an arbitrary `customer_id` from the request body and the service
   only checks it against `quote.customer_id` — this appears to be an intentional
   staff-assisted-response design (a staff member responding to a quote "on behalf of" a
   customer they're on the phone with), but it is not documented anywhere as such. Product should
   confirm whether this is an intended capability or should be restricted to `customer`-role
   callers only.
3. **Legacy `Job.checklist`/`update_checklist` deprecation.** Confirmed inert with respect to the
   authoritative completion gate and confirmed to have no frontend/mobile caller. Product should
   decide whether to formally deprecate (410) or leave as historical dead weight — not a security
   requirement either way.
4. **`create_job`/`convert_to_repair`/`spawn_repair` access-scope gap.** All three remain
   `PERMISSION_ONLY_NOT_SCOPE_AWARE` (not upgraded this slice — they are creation/spawn
   operations on a not-yet-existing or a different Job, not a same-record mutation of an existing
   job the way `assign_job`/`update_status`/the financial routes are). Whether to apply the same
   access-scope-aware upgrade is a policy question about how strictly to gate *creation*
   capabilities for read-only tenant actors, not a proven same-record bypass — deferred to a
   future slice or product call.
5. **Quote-capability routes** (`create_quote`, `create_job_quote`, `send_job_quote`) remain
   `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` at the router level, though `create_job_quote`/
   `send_job_quote` do have existing service-level ownership via
   `_get_job_for_quote_management`. Whether to add a role/permission dependency at the router
   level for defense-in-depth is a product/architecture call, not a proven bypass (no live gap
   was found — object ownership is enforced).
