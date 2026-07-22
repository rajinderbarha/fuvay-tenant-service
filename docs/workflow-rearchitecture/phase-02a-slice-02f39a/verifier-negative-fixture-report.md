# Verifier Negative Fixture Report

`verify_2f37.py --selftest`: 21/21 "fires when violated", re-run fresh in
this worktree, identical to every prior slice.

`test_phase2f39a_canonical_additions.py`'s tenant-scoping tests are
themselves negative fixtures: each proves a foreign-tenant `key_id` lookup
returns not-found (an executed failure case), not merely that a
same-tenant lookup succeeds.

`test_sprint27_notifications.py`'s two fixed tests are negative fixtures
by construction (`pytest.raises(ValueError, ...)`) — both prove access is
denied for a cross-customer and a cross-tenant caller respectively.
