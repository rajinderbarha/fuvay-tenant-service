# Known Limitations — Slice 2F-26

1. **This is still not a proven-complete application-wide figure.** 257 is what
   is now known. Confidence is much higher than the prefix-based 229 — the
   sweep is behaviour-based and covers all 2299 mounted routes — but 123
   MIXED_PERSONA mutations remain unadjudicated, and any of them could be
   tenant capabilities. The denominator can still move.

2. **7 candidate routes are held, not added.** They carry one evidence signal
   (tenant derivation OR mutation) but not both. Adding them would weaken the
   two-source rule; they are recorded in
   `generic-prefix-tenant-mutations.csv` with their verdicts.

3. **55 canonical rows disagree with the automated classifier** and were
   retained. Adjudication attributes this to indirect tenant derivation and
   service-layer delegation, not to absent capabilities. No removal was made,
   but the disagreement means the classifier is not a complete oracle.

4. **AST following is depth-2 and same-engine.** A mutation reached through
   three or more frames, or through a cross-engine helper, can still be missed.
   The same-engine restriction removes false positives at the cost of possible
   false negatives — chosen deliberately, since a false addition corrupts the
   canonical record while a false negative leaves it merely incomplete.

5. **Protection classification for the 28 additions is derived from the
   dependency chain only.** It records what guards the route declares, not
   whether the service layer enforces ownership. Those routes have not been
   audited for object ownership, actor authority or state integrity — that is
   implementation-slice work.

6. **My pre-slice baseline run was contaminated** by my own concurrent write to
   the canonical CSV and was discarded. See `environment-test-evidence.md`.

7. **Node-ID comparison remains insufficient on its own** — the reason
   behavioural invariants exist. Only one swallowed-exception path is currently
   known; others may exist in code not touched by this slice.

8. **`mutation-enforcement-matrix.csv` remains stale**, per standing convention
   since 2F-19.

9. **Slice-2D canaries untouched.** This slice added no
   `require_tenant_mutation_permission` caller, so the file count they track is
   unchanged.
