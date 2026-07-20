# Protected N01 Non-Regression Report

The 7 media routes protected by Slice 2F-31 (the `C7` set — provider
logo/shop-photo, staff profile photo, and `/v1/me/profile-photo`) were
re-verified live after this slice's changes: all remain
`STAFF_EXECUTION_ROLE_SCOPE_AWARE`/protected. No file backing those routes
(`app/engines/media/new_router.py`'s profile-photo shortcut handlers, or
`app/dependencies/auth.py::require_technician`) was touched by any change
in this slice beyond the two guard swaps on `upload_media`/`replace_media`,
which are independent routes.

Verified by: `tests/test_phase2f31_n01_media_closure.py` (34/34 passing,
including its own live re-recount at 238/262) and
`tests/test_phase2f31a_n01_residual_closure.py::TestCanonicalClosure::
test_no_other_route_status_regressed`.
