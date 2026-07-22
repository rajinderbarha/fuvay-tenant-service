# Product Decisions Required — Slice 2F-12A

## Cancellation authority — NO LONGER a product decision
Slice 2F-12 listed "should `cancel_appointment` be assignment-limited?"
as an open product question. Slice 2F-12A **resolves** it via approved
cross-module evidence (the 2F-3B-approved sibling `cancel_job`, an
identical "tenant-wide provider action") — it is intentionally
business-wide, verified, not a product decision. Removed from the open
list.

## Remaining open items (carried over, non-blocking, none cancellation-related)
1. **Note-visibility permission granularity** — whether
   `is_customer_visible` note creation should be independently
   permission-gated. No evidence either way. Not changed.
2. **`app.engines.coaching_appointment`'s own architecture and
   authorization strength** — inspected and classified
   (`DISTINCT_MODEL_DISTINCT_CAPABILITY`), not independently hardened;
   candidate for a future dedicated slice.
3. **Future technician participation in coaching** — if ever intended,
   would require explicit, evidence-backed re-authorization of both the
   mutation and cancellation guards.
4. **`actor_role="provider"` coarse audit label** — whether cancellation
   audit events should record the granular role (tenant_owner vs staff)
   instead of the generic "provider". Consistent with the approved
   sibling `cancel_job`; a non-security audit-fidelity refinement, not
   changed.
