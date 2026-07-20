# Documentation Corrections to Slice 2F-14

The following Slice 2F-14 claims were not approved and have been corrected in place (superseded
notices added to the original files, originals retained for historical record):

| File | Original claim | Correction |
|---|---|---|
| `phase-02a-slice-02f14/approval-gate.md` | `SECURITY_CLOSED` for the in-scope surface | Not closed — `void_job` had a live cross-tenant IDOR, `start_assessment`/`complete_assessment` had no named role dependency, and 5 financial routes had a permission-only access-scope gap, all present at the time this was written. Fixed in 2F-14A. |
| same | "No weaker same-record alternate route exists" (implied by the 9/28 framing) | Incorrect — the above 3 defects were exactly such weaker/missing alternates, all on the same `field_ops.Job` surface. |
| same | `PRIVACY_CLOSED` for the in-scope surface | JobNote/JobMedia's access-control gap was misclassified as an out-of-boundary distinct capability rather than a live defect. It was in fact a real, live, same-record privacy gap requiring a fix — corrected in 2F-14A (jobnote-access-control.md, jobmedia-access-control.md). |
| same | "All quality gates passed" | Not accurate given the above three findings existed unfixed at the time. |
| `phase-02a-slice-02f14/global-coverage-update.md` | 146/210 (headline) and 143/213 (direct recount) | Neither was canonical. Root cause (2 duplicate rows + 1 false-positive row + `FULLY_PROTECTED` omitted from the protected set) fully diagnosed and fixed. Canonical: **158/210**. |
| `phase-02a-slice-02f14/job-note-privacy.md` | "Not fixed this slice... does not qualify for a fix" | This was a genuine live defect, not a distinct-capability exclusion. Fixed in 2F-14A. |
| `phase-02a-slice-02f14/evidence-media-boundary.md` | JobMedia access-control gap "documented, not fixed" | Fixed in 2F-14A (ownership check now enforced; the internal/customer-visible split remains a genuine, disclosed product decision since no such column exists). |
| `phase-02a-slice-02f14/implementation-summary.md` | "7 alternate functions" vs. approval-gate's "9 same-capability alternates" | Both were correct descriptions of different, unexplained subsets — resolved in staff-alternate-route-count-resolution.md. Not a route-counting error. |

No file was deleted; every correction is an in-place superseded-notice addition preserving the
original text for audit trail, per this slice's documentation-correction requirement.
