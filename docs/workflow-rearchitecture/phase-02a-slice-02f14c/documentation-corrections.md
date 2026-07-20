# Documentation Corrections to Slice 2F-14B

| File | Original claim | Correction |
|---|---|---|
| `phase-02a-slice-02f14b/approval-gate.md` | `SECURITY_CLOSED` requirement "Zero unverified mounted same-Job routes remain" | Two mounted mutations (`add_note`, `add_media`) remained outside the 26 tool-verified protected routes at the time — `SECURITY_CLOSED` was asserted while `field_ops.router` was still 26/28, not 28/28. Fixed this slice — now genuinely 28/28. |
| `phase-02a-slice-02f14b/approval-gate.md` | Framing of `add_note`/`add_media` as having a fix that is merely "tool-invisible by convention" (implying router-level enforcement was optional) | Corrected: the service-level fix was real, but the **absence** of any router-level persona/mutation-scope dependency was an actual, unverified gap — no test anywhere proved a read-only-scoped tenant account was denied. This was not "optional defense-in-depth," it was a missing required layer, consistent with this slice's Workstream 4 instruction not to rely on service-level object access as a replacement for mutation-scope policy. |
| `phase-02a-slice-02f14b/implementation-summary.md` | "field_ops subtotal: 29/40 → 38/40" presented without flagging the 2 remaining rows as an open item requiring resolution in a specific follow-up | Corrected: this slice explicitly reconciles and closes those 2 rows to 40/40 — see field-ops-coverage-reconciliation.md. |
| `phase-02a-slice-02f14b/known-limitations.md` item (implicit) | `create_job`'s FK fields framed as inherently out of scope / not a security matter | `service_type_id`, `parent_job_id`, and `booking_id` are all tenant-owned references that had **zero** ownership validation (not merely "unhardened") — a valid record belonging to a different tenant would have been silently accepted. This was a real gap, fixed this slice, not merely a hardening nicety. |

No file was deleted. A superseded notice is added to `phase-02a-slice-02f14b/approval-gate.md`
per the established pattern from prior slices' own corrections.
