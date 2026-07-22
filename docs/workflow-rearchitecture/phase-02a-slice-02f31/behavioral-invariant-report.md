# Behavioral Invariant Report - Slice 2F-31

Closed-module canaries pass. StaffPermission semantics re-asserted. M01 fully
intact. One application file modified (`app/engines/media/new_router.py`);
the change is a guard swap between two dependencies with an identical
admitted-role set, so no authorization behaviour narrows or widens beyond
adding the access-scope denial - the intended effect.
