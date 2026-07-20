# Documentation Corrections to Slice 2F-14A

| File | Original claim | Correction |
|---|---|---|
| `phase-02a-slice-02f14a/known-limitations.md` item 3/4 | `create_job`/`convert_to_repair`/`spawn_repair` remaining `PERMISSION_ONLY_NOT_SCOPE_AWARE` was framed as a scope-only product question ("creation/spawn capabilities, not same-record mutations of an existing job under contention") | `spawn_repair` in fact had **zero ownership check at all** (a live cross-tenant IDOR) and **zero duplicate-repair guard** — not merely an access-scope nuance. This was a security defect, not a product-policy question. Fixed in 2F-14B. |
| `phase-02a-slice-02f14a/known-limitations.md` item 4 | Quote-capability routes' router-level gap was framed as "existing service-level ownership already adequate on inspection" | Incorrect for `create_quote` (no service-level ownership existed at all) and for `create_job_quote`/`send_job_quote` (`_get_job_for_quote_management` never denied `customer` — a customer could administer a provider quote). "Adequate on inspection" was not an accurate characterization. Fixed in 2F-14B. |
| `phase-02a-slice-02f14a/product-decisions-required.md` item 2 | `respond_to_quote`'s non-customer `customer_id` handling was framed as "an intentional staff-assisted-response design... not yet documented as such" — a `PRODUCT_DECISION_REQUIRED` | This was a confirmed **customer-impersonation defect** with no established offline-decision policy (no audit trail, no documentation, no test proving intent) — per this slice's explicit instruction, absence of a canonical customer caller is not evidence that impersonation is acceptable. Fixed in 2F-14B, not left as a product question. |
| `phase-02a-slice-02f14a/approval-gate.md` | "Zero unverified mounted same-Job routes remain among the same-record-same-capability set" | This applied only to the 9 routes in scope for 2F-14A; `field_ops.router` still had 11 unclassified/unfixed routes at the time (create_job, convert_to_repair, spawn_repair, and 5 quote routes + respond_to_quote), 2 of which (spawn_repair's IDOR, the quote-persona gaps) were live defects, not merely unclassified. This slice (2F-14B) closes 9 of those 11. |

No file was deleted; corrections are disclosed here rather than retroactively editing 2F-14A's
files, since 2F-14A's own files already carry forward-pointing "see Slice 2F-14B" references
where updated (mutation-enforcement-matrix.csv, tenant-mutation-endpoint-inventory.csv). A
superseded-notice is added to `phase-02a-slice-02f14a/approval-gate.md` per the established
pattern from 2F-14A's own correction of 2F-14.
