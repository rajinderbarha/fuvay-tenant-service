# Selection Verifier Spec - Slice 2F-30

`scripts/workflow_rearchitecture/verify_selection_2f30.py` - 21 conditions
(Q01-Q21): coverage 226/259; unprotected 33; queue equals the live set; no
protected route in the queue; **no M01 route in the queue and all 12 M01 routes
still protected**; no held candidate counted; module counts sum to 33; no route
in two modules; exactly one module selected; Sets A/B/C frozen at their hashes
with Set B never treated as canonical; all 59 held cross-referenced; no critical
observation omitted; contract omits no Set A route and smuggles no Set C route;
canonical and matrix hashes unchanged; no document claims implementation.

Each condition has an executed negative fixture (`--selftest`).
