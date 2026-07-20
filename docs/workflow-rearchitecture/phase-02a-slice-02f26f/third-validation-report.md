# Third Holdout Validation Report — Slice 2F-26F

## Result: 21/24 all-field agreement. Required 24/24. **Gate fails.**

| Field | Agreement |
|---|---|
| Persona | **24/24** |
| Tenant direction | **24/24** |
| Capability action | **24/24** |
| Abstention reason | **24/24** |
| Side effect | 23/24 |
| Capability family | 22/24 |
| **All six** | **21/24** |

Trajectory across three independent holdouts: **4/24 → 19/24 → 21/24**.

The authorization-critical fields — persona, tenant direction and abstention —
are now perfect on a fresh, disjoint, blinded sample. D-01 through D-06 all
hold. **Every remaining failure is in the capability-taxonomy layer this slice
introduced**, not in authority reasoning.

## Freeze ordering

| Event | Hash |
|---|---|
| Eligible population (75 routes) | `479d87403ccd131b` |
| Holdout manifest | `f3e0aa8e130529c4` |
| Manual verdicts | `066b2f8b967eacc8` |
| Manual evidence review | `99e8e8c87f56a253` |
| Classifier at freeze | `c3a0954bcc62c6e5` |
| Request model at freeze | `8cfb6b90b57c4db4` |

Manifest, manual verdicts and evidence review were all frozen before the
classifier ran on this holdout. All hashes asserted in tests.

## The three disagreements

### 1-2. Capability-family prefix precedence (2 routes) — real tooling defect

`_FAMILY_BY_PREFIX` is an ordered list, and the general rules sit above the
specific ones:

- `^/v1/tenants?\b` matches `/v1/tenant/service-areas/...` before the
  `geography_serviceability` rule → returned `tenant_governance`.
- `^/v1/me\b` matches `/v1/me/profile-photo` before the `media` rule →
  returned `identity_access`.

Ordering bug, not a modelling one. Both are single-line fixes. Deliberately
not fixed — see below.

### 3. `GET /v1/ds/tenants/{tenant_id}/pricing/recommendations` — write-regex false positive

The side-effect pattern includes `\.is_active\s*=`, intended to catch an
assignment. It also matches the **equality** in
`select(CityTierConfig).where(CityTierConfig.is_active == True)`. A pure read
was reported as `DATABASE_MUTATION`.

**Found by the WS5 evidence-review checklist**, not by the comparison: the
checklist requires explicitly testing the mutating-GET possibility, so I
verified with a stricter pattern (`db.add|delete|add_all|merge|commit|flush`)
and confirmed no real write. That same checklist confirmed the *genuine*
mutating GET on `/customers/{customer_id}/ltv` (`self.db.add(s)` + `flush`),
which I would otherwise have recorded as a pure read — exactly the mistake I
made in 2F-26E.

## Why nothing was fixed

All three defects were found by, or while adjudicating, the holdout that
measures the classifier. Repairing them and re-running this holdout would be
the circular proof the mission forbids. This holdout is now burned.

## Abstention contract

Manual abstained on 3 routes; the tool abstained on exactly the same 3 with
matching reason codes (`OWNERSHIP_CHECK_IN_SERVICE_NOT_TRACEABLE`). Zero
avoidable abstentions (verifier N31). No abstained route contributes to any
canonical decision.

## Consequence

Zero canonical edits. Canonical `45244cd9540456db` and matrix
`4c7c3bce02096a43` preserved. **GLOBAL_COVERAGE_RECONCILIATION_BLOCKED.**
