# Documentation Corrections — Slice 2F-25

## 1. Slice 2F-24's `DISTINCT_MODEL` classification — CONFIRMED and vindicated

2F-24 classified `app.engines.review` as `DISTINCT_MODEL`, declined to change
it, and flagged it as a stronger future candidate than an "orphaned legacy"
framing suggested. **All of that was correct.** The tables really are distinct
(`reviews` vs `customer_reviews`), so it was not a same-record bypass, and
touching it would have exceeded that mission's boundary.

This slice confirms the flag was warranted: the exposure was **larger** than
the canonical engine's — cross-tenant mutation *and* cross-tenant enumeration
via client-supplied `tenant_id` on six read paths.

## 2. Refinement to 2F-24's characterisation

2F-24 described the legacy engine as carrying "the same unguarded shape" as
the canonical defect. Accurate but incomplete: the legacy engine additionally
accepted `tenant_id` from the query string, path and request body across six
routes, and its `_assert_owns` guard only ever applied to the customer role.
Recorded here rather than left implicit.

## 3. The canonical denominator was incomplete, not incorrect

The 226 figure was never wrong by counting — it was **complete only within the
prefix convention it was built on**. Three mounted tenant mutations on a
generic prefix had no canonical row. Denominator 226 -> 229 by exact route
evidence. This is a methodology finding, recorded in
`known-limitations.md` #1 because the same blind spot may exist elsewhere.

## 4. Self-correction during this slice: a vacuous test assertion

The first draft of the scoping tests asserted
`"tenant_id" in str(compiled_statement)`. That is **vacuous** — every
`SELECT reviews.*` lists `reviews.tenant_id` as a column, so the assertion
passes even when the query is entirely unscoped. It was caught only because
the *negative* case (super_admin, expected unscoped) failed for the same
reason. Both were rewritten to inspect the **WHERE clause** via a `_where()`
helper whose docstring records the trap.

Had only the positive assertions existed, they would have "passed" while
proving nothing.

## 5. Forward annotation added to Slice 2F-24
Per the established convention.

## 6. Slice-2D canaries untouched
The `require_tenant_mutation_permission` file count moved 8 -> 9 because this
slice adopted that existing dependency. The canary was already failing and
still fails with an identical node ID — no rewrite, no state change.
