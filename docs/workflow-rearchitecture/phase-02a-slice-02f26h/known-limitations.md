# Known Limitations — Slice 2F-26H

1. **The classifier did not reach 100% independent agreement.** The fifth and
   final holdout scored 22/24. The two misses are adjudication-boundary cases
   where the tool's answer is arguably stronger than the frozen manual verdict,
   but the contract requires exact agreement and it was not met.

2. **The original 123-route population is exhausted for independent
   validation.** All five 24-route holdouts (120 routes) are burned; the 3
   reserve routes are insufficient alone (WS16). No sixth holdout may be built
   from burned routes.

3. **Manual adjudication is the current weak link, not the classifier.** On
   this holdout the tool was at least as defensible as the manual on both
   disagreements. Independent validation is limited by single-reviewer manual
   precision; WS16 strategy 1 (dual-review) or strategy 3 (external reviewer)
   would address this.

4. **Action inference depends on a synonym table and stopword list.** Both are
   documented and frozen, but a verb that is also a common noun (`request`,
   `export`, `check`) sits on a boundary the token model resolves by position
   and stopwords, not by semantics. `request_export` -> export is the visible
   example.

5. **Capability family/action remain path/name-derived, not model-derived.**

6. **Security observations are static-reading only.** None executed.

7. **Prior-slice models remain on disk unmodified.** 26H composes 26G, which
   composes 26F/26E and the 26B resolver.
