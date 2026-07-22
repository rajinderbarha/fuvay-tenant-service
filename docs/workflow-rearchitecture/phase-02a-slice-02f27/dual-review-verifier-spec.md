# Dual-Review Verifier Spec - Slice 2F-27

verify_dualreview_2f27.py - 12 conditions (V01-V12): population-hash frozen,
both reviewers cover all routes, files non-identical, taxonomy valid, every
disagreement resolved, partition covers 123 once, no route unresolved,
canonical+matrix unchanged, recount 214/257, no premature reconciliation claim.
Each has an executed negative fixture; --selftest forces each to fail.
