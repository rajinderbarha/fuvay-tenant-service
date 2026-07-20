# Verifier Negative-Fixture Report (WS18)

`python scripts/workflow_rearchitecture/verify_2f35.py --selftest`
forces each condition's state key `False` in turn and confirms the
condition actually reports failure.

**Result: 22/22 fire when violated. SELFTEST PASSED.**

Same `st.get(key, real_condition)` override mechanism used by every
prior slice's verifier in this program.
