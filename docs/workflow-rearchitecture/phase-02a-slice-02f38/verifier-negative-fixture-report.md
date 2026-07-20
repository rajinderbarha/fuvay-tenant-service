# Verifier Negative Fixture Report

`python scripts/workflow_rearchitecture/verify_2f37.py --selftest` run
fresh in this worktree: **21/21 "fires when violated" confirmed**, i.e.
every one of the 21 existing rules was independently confirmed to
correctly detect its own violation (not merely to pass on the current
good state). Raw output captured this session, all 21 lines read
"PASS ... -- fires when violated".

This confirms the 21 existing rules are real detectors, not tautologies
that would pass regardless of the underlying state. See
`slice-2f38-verifier-spec.md` for which additional 2F-38-specific failure
conditions have **no** existing negative fixture (an honest gap, not
claimed covered).
