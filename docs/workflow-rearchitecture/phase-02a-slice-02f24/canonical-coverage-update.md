# Canonical Coverage Update — Slice 2F-24

## Starting approved baseline
**207 protected / 226 total**, 19 unprotected across 8 modules.

## Per-route reconciliation (the two selected routes, individually)

### `POST /v1/provider/reviews/{review_id}/reply` — FULLY PROTECTED
| Dimension | Status |
|---|---|
| Persona | `require_tenant_owner_mutation` |
| Mutation scope | read-only denied |
| Tenant ownership | central scoped lookup |
| Object ownership | same (review is the object) |
| Actor attribution | server-derived id + truthful ACTOR_PROVIDER |
| State integrity | one reply per review preserved |
| Alternate-route closure | admin reply moderation is super_admin |
| Service-layer safety | scoped lookup inside the service |
| No partial persistence | proven |
| Read/privacy | detail read scoped |

### `POST /v1/provider/reviews/{review_id}/flag` — FULLY PROTECTED
Same ten dimensions, plus: flag tenant taken from the review, actor-type
allow-list, and provider flagging cannot reach any admin moderation outcome.

## Arithmetic
- Numerator: 207 + 2 = **209**
- Denominator: 226 + 0 - 0 - 0 - 0 - 0 = **226**
- Unprotected: **17**
- Remaining modules: 8 - 1 = **7**... corrected: **6** modules remain, since
  `customer_reviews.provider_router` was the whole of one module and the other
  seven modules in the 2F-23 queue are unchanged. See the note below.

**Module count note:** the 2F-23 queue listed 8 modules. This slice closed one
of them entirely (both of its routes), so **7 modules / 17 routes remain**.
`remaining-module-queue-update.csv` enumerates them and its route counts sum
to 17.

Counted live from the CSV, not asserted: `protected 207 -> 209, total 226,
remaining 17`.

## The customer flag route is NOT counted
`POST /v1/customer/reviews/{review_id}/flag` was corrected this slice (client
tenant authority removed, self-scoped ownership added), but it carries a
`/v1/customer/` prefix and is therefore outside the tenant-only canonical CSV
by the Design A convention held since 2F-15C. **It does not move the
numerator or the denominator.** It is reported separately here and in
`customer-flag-authority.md`, exactly as the mission requires.

Likewise the two read-IDOR fixes (provider and customer detail reads) are
privacy corrections on GET routes, which the mutation-only canonical CSV does
not track at all.

## Every numeric recount assertion updated
Located by repository-wide grep before declaring reconciliation complete:

| File | Change |
|---|---|
| `test_phase2f14a_...py` | `protected == 207` -> `209` |
| `test_phase2f17a_...py` | `protected == 207` -> `209` |
| `test_phase2f19_...py` | `protected == 207` -> `209`; remainder `19` -> `17` |
| `test_phase2f21_...py` | live-canonical `207` -> `209` (two expression forms); remainder `19` -> `17` |
| `test_phase2f23_...py` | live-canonical `207` -> `209`; remainder `19` -> `17` |
| `test_phase2f24_...py` (new) | asserts the post-state |

## Historical artifacts NOT rewritten
2F-19 (26 rows / 10 modules), 2F-21 (20 / 9) and 2F-23 (19 / 8) slice CSVs are
untouched. Where a later slice protected a route those CSVs recorded as
unprotected, the *test* carries a narrow, slice-named exemption instead --
preserving each slice's truthful point-in-time finding.

## Second canonical CSV
`mutation-enforcement-matrix.csv` remains the legacy per-domain summary whose
TOTAL predates 2F-17A; not the authoritative denominator, not forced to match,
consistent with 2F-19 through 2F-23.
