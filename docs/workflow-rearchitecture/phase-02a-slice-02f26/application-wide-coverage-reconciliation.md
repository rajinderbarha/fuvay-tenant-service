# Application-Wide Coverage Reconciliation — Slice 2F-26

## Arithmetic

**Numerator**
212 previous protected
+ 2 newly discovered already-protected tenant mutations
- 0 incorrectly counted protected rows
= **214**

**Denominator**
229 previous
+ 28 newly discovered tenant/provider mutations (two-source evidence each)
- 0 false positives
- 0 duplicates
- 0 customer/admin/internal routes
- 0 deprecated/disconnected rows
= **257**

**Unprotected: 257 - 214 = 43**

Counted live from the CSV, not asserted: `denominator 229 -> 257,
numerator 212 -> 214, unprotected 17 -> 43`.

## Population report

| Category | Count |
|---|---|
| Mounted routes (excl. HEAD/OPTIONS) | 2299 |
| Genuine mutations by side effect | 1058 |
| TENANT_PROVIDER_MUTATION | 209 |
| PLATFORM_ADMIN_MUTATION | 617 |
| CUSTOMER_SELF_SERVICE_MUTATION | 77 |
| MIXED_PERSONA_MUTATION | 123 |
| PUBLIC / TRUSTED_CALLBACK | 32 |
| Mutating GET routes | 31 |
| Read-only POST/PUT/PATCH | 145 |
| Missing canonical rows | 35 candidates -> 28 confirmed |
| Rows added | 28 |
| Rows removed | 0 |
| Duplicate canonical keys | 0 |
| Unclassified routes | 0 |

## The 28 additions

12 on `/v1/auth` (MFA, password, staff invite/permissions/deactivate,
impersonation, API keys), 9 across `/v1/media` and `/v1/me`, 4 on
`/v1/enterprise`, 3 on `/v1/commerce`, plus `/v1/bookings` and `/v1/rag`.

Every one carries recorded two-source evidence in `canonical-row-diff.csv`:
the tenant-derivation expression and the mutation expression. A route with
only one of the two was **held**, not added — 7 such holds remain.

## Why no removals

55 canonical rows did not match the automated classifier. Adjudication
(`prefixed-route-false-positive-audit.csv`) classifies them:

| Verdict | Count | Meaning |
|---|---|---|
| KEEP_TENANT_SOURCE_INDIRECT | 34 | mutation confirmed; tenant derived through the service layer |
| REVIEW_NO_DIRECT_MUTATION_EVIDENCE | 20 | thin handler delegating to a service |
| CLASSIFIER_LIMITATION_KEEP | 1 | evidence confirms tenant mutation; the automated pass missed it |

None is evidence that a capability is absent. **Zero rows removed.**

## Both canonical CSVs

`tenant-mutation-endpoint-inventory.csv` is the authoritative row-level source
and recounts at 257/214.

`mutation-enforcement-matrix.csv` remains the legacy per-domain summary whose
TOTAL predates 2F-17A — not the authoritative denominator, not forced to
match, consistent with every slice since 2F-19.

## Historical artifacts
2F-19, 2F-21, 2F-23 and 2F-25 point-in-time slice CSVs are untouched.
