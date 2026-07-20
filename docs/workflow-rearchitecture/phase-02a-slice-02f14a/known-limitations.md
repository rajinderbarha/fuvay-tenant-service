# Known Limitations

1. `add_note`/`add_media` remain `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` in the runtime
   dependency-introspection tool's own classification, despite being genuinely fixed at the
   service layer (see jobnote-access-control.md, jobmedia-access-control.md). The canonical
   coverage figure (158/210) does **not** count these two routes as protected, since the fix is
   tool-invisible by the same convention applied throughout this whole initiative — this
   deliberately understates the true security posture rather than overstate it.
2. `JobMedia` has no internal/customer-visible split — see product-decisions-required.md item 1.
3. `create_job`, `convert_to_repair`, `spawn_repair` remain `PERMISSION_ONLY_NOT_SCOPE_AWARE`
   (not fixed this slice — creation/spawn capabilities, not same-record mutations of an existing
   job under contention).
4. `create_quote`, `create_job_quote`, `approve_job_quote`, `reject_job_quote`, `send_job_quote`,
   `respond_to_quote` remain `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK`/`ROLE_CHECK_INLINE_NOT_TOOL_VISIBLE`
   at the router level — distinct capability (quotes), existing service-level ownership was found
   adequate on inspection and not modified.
5. `respond_to_quote`'s non-customer `customer_id` handling is a design ambiguity, not a proven
   bug — see product-decisions-required.md item 2.
6. The global coverage figure (158/210) reflects the `tenant-mutation-endpoint-inventory.csv` as
   maintained across all prior slices; a full independent re-verification of every non-field_ops
   row (all rows outside the 40 field_ops-related ones) was not re-run from scratch this slice —
   this slice corrected the 3 specific row-level defects found (2 duplicates + 1 false positive)
   and the 1 categorization omission (`FULLY_PROTECTED`) rather than re-deriving all 170
   non-field_ops rows from a fresh runtime scan of 15+ other engines, which is out of scope for a
   focused field_ops continuation.
