# Canonical Coverage Reconciliation — Slice 2F-25

## Starting point (provisional)
**209 protected / 226 total**, treated as provisional pending legacy
classification exactly as the mission required.

## The finding that moved the denominator

The canonical CSV's Design A convention (established 2F-17A) identifies
tenant-facing routes by **path prefix**: `/v1/provider/`, `/v1/staff/`,
`/v1/tenant/`. The legacy review engine mounts at the generic `/v1/reviews/*`,
so its tenant mutations were **never candidates** for the sweep — not
excluded on evidence, simply never considered.

Three of them are genuine tenant/provider mutations:

| Route | Evidence |
|---|---|
| `POST /v1/reviews/{review_id}/reply` | `P.TENANT_UPDATE`; mutates a tenant-owned review |
| `POST /v1/reviews/{review_id}/flag` | tenant persona after this slice; mutates `review.status` |
| `POST /v1/reviews/requests` | `P.TENANT_UPDATE`; creates a tenant-owned `ReviewRequest` |

Two are correctly outside:

| Route | Classification |
|---|---|
| `POST /v1/reviews/{review_id}/resolve` | `PLATFORM_ADMIN_OUTSIDE_XY` (`require_super_admin`) |
| `POST /v1/reviews` | `DEPRECATED` (410 GONE — mutates nothing) |

## Arithmetic

**Denominator**
226 + 3 newly discovered tenant mutations − 0 false positives − 0 duplicates
− 0 customer/admin/internal − 0 deprecated = **229**

**Numerator**
209 + 0 newly-protected existing rows + 3 newly-protected newly-discovered
rows − 0 incorrectly counted = **212**

**Unprotected: 229 − 212 = 17** (unchanged — the three arrived and were
protected in the same slice)

Counted live from the CSV, not asserted: `denominator 226 -> 229,
numerator 209 -> 212, unprotected 17 -> 17`.

## Full report

| Category | Count |
|---|---|
| Existing canonical tenant routes | 226 |
| Newly discovered tenant routes | 3 |
| Customer mutations (outside X/Y) | 0 in this engine |
| Platform-admin mutations (outside X/Y) | 1 (`resolve_flag`) |
| Internal mutations | 0 |
| Deprecated routes | 1 (`POST /v1/reviews`) |
| Protected legacy routes | 3 |
| Blocked legacy routes | 0 |
| **Final tenant X/Y** | **212 / 229** |
| Remaining unprotected | 17 |
| Remaining modules | 7 |

## Why this was not forced to 209/226
The mission explicitly warned against forcing the arithmetic. The honest
outcome is that the previous denominator was **incomplete**, not wrong-by-
counting: three mounted tenant mutations had no canonical row. Hiding them to
preserve a tidy 209/226 would have been the failure mode the mission named.

## Recount assertions updated
`test_phase2f14a`, `test_phase2f17a`, `test_phase2f19`, `test_phase2f21`,
`test_phase2f23` — all live-canonical assertions moved to 229/212, each
annotated. New `test_phase2f25` asserts the post-state and that the three
legacy rows are present and protected.

## Historical artifacts NOT rewritten
2F-19 (26/10), 2F-21 (20/9) and 2F-23 (19/8) slice CSVs are untouched.

## Second canonical CSV
`mutation-enforcement-matrix.csv` remains the legacy per-domain summary whose
TOTAL predates 2F-17A — not the authoritative denominator, not forced to
match, consistent with 2F-19 through 2F-24.
