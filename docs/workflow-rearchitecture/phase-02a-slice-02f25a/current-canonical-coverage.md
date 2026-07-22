# Current Canonical Coverage — Slice 2F-25A

## CURRENT_CANONICAL_COVERAGE

**212 protected of 229 currently known tenant/provider mutations.
17 currently unprotected. 7 currently queued modules.**

Unchanged by this slice: no route was added, removed or reclassified.

## Why the arithmetic does not move

This slice closed three **reads** and hardened one **mutation**. The canonical
CSV tracks mutations only, so:

- the three reads have no denominator effect (none was ever misclassified as
  a mutation — verified);
- `create_request` retains its existing row and its
  `TENANT_MUTATION_PERMISSION_SCOPE_AWARE` status.

## create_request: reconciled individually

2F-25 marked it protected on the strength of tenant pinning alone. That was
premature — `job_id` and `customer_id` were still client-supplied and
unverified.

| Dimension | 2F-25 | 2F-25A |
|---|---|---|
| Persona | permission-gated | unchanged |
| Mutation scope | scope-aware | unchanged |
| Tenant authority | principal-derived | unchanged |
| **Parent Job ownership** | **ABSENT** | **PROVEN** — `field_ops.Job` by `job_number` within tenant |
| **Customer authority** | **client-supplied** | **derived from the Job** |
| Duplicate-check ordering | leaked foreign job numbers | ownership first |
| No partial persistence | untested | proven |

It therefore **retains** its classification, but now earns it. Had the parent
relationship remained ambiguous, the mission required removing the
FULLY_PROTECTED status — that was a real possible outcome, avoided by proving
the lineage rather than by asserting it.

## Report

| Category | Count |
|---|---|
| Current canonical numerator | **212** |
| Current canonical denominator | **229** |
| Protected create_request | 1 (proven this slice) |
| Blocked create_request | 0 |
| Customer/admin/internal routes (outside X/Y) | `resolve_flag` (super_admin), `POST /v1/reviews` (410) |
| Current unprotected | **17** |
| Current module count | **7** |

## This is NOT application-wide completeness

The label is **CURRENT_CANONICAL_COVERAGE**, deliberately.

Slice 2F-25 demonstrated that the prefix-based Design A sweep
(`/v1/provider|staff|tenant/*`) never considered the legacy engine's
`/v1/reviews/*` routes — three genuine tenant mutations had no canonical row.
The same blind spot may hide routes on other generic prefixes in other
engines.

Until a persona-based application-wide sweep is performed, 229 is **the
count of what is currently known**, not a proven total.

The verifier enforces this mechanically: it fails if any document in this
slice uses the forbidden completeness label. That check fired against an
earlier draft of *this very file*, which quoted the label inside a sentence
disclaiming it -- a blunt check cannot distinguish a claim from a denial, and
the blunt behaviour is correct. The wording was changed rather than the
check weakened.
