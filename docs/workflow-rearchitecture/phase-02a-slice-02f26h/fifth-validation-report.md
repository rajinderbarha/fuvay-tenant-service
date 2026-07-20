# Fifth (Final) Holdout Validation Report — Slice 2F-26H

## Result: 22/24 all-field agreement. Required 24/24. **Gate fails.**

| Field | Agreement |
|---|---|
| Side effect | **24/24** |
| Capability family | **24/24** |
| Capability action | 23/24 |
| Persona | 23/24 |
| Tenant direction | 23/24 |
| **All five** | **22/24** |

Across five independent holdouts: **4 → 19 → 21 → 23 → 22**.

D-09 is repaired: `POST /v1/tenants/{tenant_id}/engines/bulk-disable` and every
tokenization fixture resolve correctly, and no POST silently defaults to
`create`. The two remaining disagreements are **not** D-09 regressions — they
are adjudication-boundary cases, described honestly below.

## Freeze ordering

| Artifact | Hash |
|---|---|
| Eligible population (27) | `2d206d745cadb84b` |
| Holdout manifest | `d968bad8957a7159` |
| Reserve set (3) | `9c73ee22f54d71ac` |
| Manual verdicts | `3efb58958c74aae8` |
| Evidence review | `9d7707a11ec0ee66` |
| Action model at freeze | `920e6b4c3e912673` |

Manifest, manual verdicts and evidence review all frozen before the classifier
ran on this holdout. All asserted in tests.

## The two disagreements — both adjudication-boundary, not tool defects

### 1. `POST /v1/compliance/portability-requests`

- Manual action: `REQUIRES_MANUAL_ACTION_ADJUDICATION`
- Tool action: `export`

The service method is `request_export`. The tokenizer skips `request` (a noun
stopword) and reaches `export`, a mapped verb — so the tool concluded `export`.
On reflection the **tool is defensible**: `request_export` *is* an export
operation. My manual verdict abstained because I read `request_export` as
having no leading verb; that was a manual-adjudication miss, not a tool defect.

### 2. `POST /v1/serviceability/check`

- Manual persona/direction: `TENANT_PROVIDER_MUTATION` / `OBJECT_DERIVED_TENANT`
- Tool persona/direction: `REQUIRES_MANUAL_ADJUDICATION` / `REQUIRES_MANUAL_TENANT_ADJUDICATION`

The handler derives `customer_id` from the principal when the caller is a
customer, and carries no tenant. The tool correctly saw self-referential
identity with no ownership predicate and **abstained** — the conservative,
defensible call. My manual verdict over-reached by assigning a tenant persona
from the path prefix. Again the tool is arguably the stronger of the two.

## Honest framing

On both disagreements the **tool's answer is at least as defensible as my
manual answer** — in one case more so. But the contract is exact agreement
between a manual verdict frozen *before* the classifier ran and the classifier
output, and that is what failed. WS15 forbids revising the manual to match the
tool and re-scoring; doing so would manufacture a pass. So the honest result is
22/24, and it blocks.

## WS16 — final-holdout policy

This was the **last independent holdout** the original 123-route population can
supply. All five 24-route holdouts (120 of 123 routes) are now burned; only the
three-route reserve set remains, which WS16 states is insufficient to establish
a new independent validation result.

**Classifier-driven canonical reconciliation on this population is exhausted.**
The classifier is materially improved across nine defects (D-01…D-09) but has
**not** reached 100% independent agreement on a held-out sample. No sixth
holdout may be constructed from burned routes.

### Allowed later strategies (process choices, not executed here)

1. Full manual dual-review adjudication of the entire remaining population.
2. Validation against a different untouched route population (outside the
   original 123 mixed-persona set).
3. An independent external reviewer / second-implementation cross-check.
4. Retain the current canonical inventory as-is and process each module
   manually when it is selected for implementation.

## Consequence

Zero canonical edits. Canonical `45244cd9540456db` and matrix
`4c7c3bce02096a43` preserved. **GLOBAL_COVERAGE_RECONCILIATION_BLOCKED.**
