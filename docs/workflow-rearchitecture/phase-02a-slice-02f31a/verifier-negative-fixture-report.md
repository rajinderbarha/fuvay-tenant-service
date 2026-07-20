# Verifier Negative-Fixture Report (WS13)

`python scripts/workflow_rearchitecture/verify_n01_2f31a.py --selftest`
forces each condition's underlying state key to `False` in turn and asserts
the condition actually reports failure — proving R01–R21 are load-bearing
checks, not tautologies that always pass regardless of input.

Result: **21/21 fire when violated. SELFTEST PASSED.**

This mirrors the established pattern from every prior slice's verifier
(`verify_n01_2f31.py`, `verify_m01_2f29.py`, `verify_selection_2f28.py`,
`verify_selection_2f30.py`, `verify_dualreview_2f27.py`) — all use the same
`st.get(key, real_condition)` override mechanism so `conditions({key:
False})` deterministically fails exactly that one check.
