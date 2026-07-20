# Known Limitations — Slice 2F-26G

1. **D-09 remains open** — the capability-action table matches `/disable\b`
   but not the hyphenated `bulk-disable`. Deliberately unfixed: it was found by
   the holdout that measures the classifier, so its repair must be validated
   against a fresh fifth holdout.

2. **All four holdouts are now burned.** 27 of the original 123 mixed-persona
   routes remain unsampled — enough for exactly one more holdout of this size.
   After that, independent validation of this population is exhausted.

3. **Five strata have zero eligible members** in the remaining 51: principal-
   tenant nested-specific, provider surface, customer self-service, internal
   branch, trusted callback. Declared not representable; behavioural fixtures
   cover the runtime cases separately.

4. **Capability action is still pattern-based**, now shown to have the same
   literal-pattern fragility (D-09) the family layer had (D-07). A more
   robust action model would derive the verb from the path's final segment
   token-by-token rather than by slash-anchored regex.

5. **Capability family is path-shape based, not model-derived.** The
   deterministic precedence contract removes shadowing but the family still
   comes from the URL, not from the mutated model.

6. **AST write detection does not follow calls beyond one service hop.** It
   resolves the handler and its directly-called service methods; a write two
   calls deep would be missed. It is not a full data-flow analysis.

7. **Security observations are static-reading only.** None executed.

8. **Prior-slice models remain on disk unmodified.** 2F-26G composes 2F-26F,
   which composes 2F-26E and the 2F-26B resolver; none is deleted.
