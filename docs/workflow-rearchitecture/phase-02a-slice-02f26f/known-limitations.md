# Known Limitations — Slice 2F-26F

1. **Three classifier defects remain open**, deliberately unfixed because the
   holdout that found them cannot then validate their repair:
   - capability-family prefix precedence (2 routes)
   - write-regex equality false positive (`.is_active ==` read as assignment)

2. **All three holdouts are now burned.** 51 of the original 123 mixed-persona
   routes remain unsampled — enough for two more holdouts of this size.

3. **Four strata have zero eligible members** in the remaining population:
   provider surface, customer self-service, internal branch, trusted callback.
   Declared as not representable, not claimed as covered. Behavioural
   fixtures cover the runtime cases (grant, deny, cross-tenant isolation,
   unknown role) independently of route membership.

4. **Capability family/action is derived from path shape**, not from the
   mutated model. That is why the precedence bug produced wrong families; a
   model-derived family would be stronger.

5. **Side-effect detection remains regex-plus-qualified-call.** It has now
   produced both a true positive the manual pass missed (`/ltv`) and a false
   positive (`/pricing/recommendations`). It is not a data-flow analysis.

6. **Semantic role assignment defaults to `ACTOR_IDENTITY`** for a principal in
   an unrecognised callee slot. This is deliberately fail-closed — it cannot
   manufacture scope — but it means precision depends on the slot-name
   vocabulary.

7. **Security observations are static-reading only.** None executed.

8. **The 2F-26B resolver and 2F-26E model remain on disk unmodified.** The
   2F-26F model composes them rather than replacing them.
