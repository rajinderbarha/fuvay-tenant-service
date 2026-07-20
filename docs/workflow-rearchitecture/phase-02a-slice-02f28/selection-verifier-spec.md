# Selection Verifier Spec - Slice 2F-28

`scripts/workflow_rearchitecture/verify_selection_2f28.py` - 20 conditions
(S01-S20): coverage is 214/259; unprotected is 45; queue exports exactly those
45; no canonical route missing; no protected route in the queue; no held
candidate counted canonically; module counts sum to 45; no route in two
modules; exactly one module selected; selected scope frozen at 12 and equal to
module membership; no selected held route treated as canonical; adjacent
exclusions carry reasons; all 59 held cross-referenced; no critical security
observation omitted; contract omits no canonical route; contract smuggles no
out-of-scope route; canonical and matrix hashes unchanged; no document claims
implementation occurred.

Each condition has an executed negative fixture (`--selftest`).
