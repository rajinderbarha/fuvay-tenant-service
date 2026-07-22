# Slice 2F-39A Verifier Spec

A dedicated `verify_2f39a.py` covering all ~20 mission-specified failure
conditions was **not built this slice** — same honest gap pattern as
2F-38/2F-39, given the time this slice's actual classification and
notification-fix work required.

## What exists as real, executable evidence instead

- `verify_2f37.py` (21/21 PASS, reconfirmed at slice start) — unchanged,
  covers the original 313-route canonical set (now a proper subset of the
  true 321).
- `tests/test_phase2f39a_canonical_additions.py` (4 tests) — proves the 3
  api-key routes' tenant-scoping is real (server-derived tenant_id,
  foreign-tenant lookups return not-found).
- `tests/test_sprint27_notifications.py` (44 tests, both previously-failing
  ones now fixed) — proves cross-customer and cross-tenant chat access is
  denied.

## Gaps

- No automated check that all 2,320 mounted routes are classified (229
  remain genuinely unclassified this slice — see `known-limitations.md`).
- No automated check that `admin_readonly` cannot mutate the 5 newly
  added routes lacking dedicated tests (`invite_staff`,
  `update_permissions`, `deactivate_staff`, `resend_invite`,
  `update_staff_schedule`).
- No negative fixture proving a role alias reintroduced into
  `canonical_seed_final_l5_01.py`/`seed_demo_users.py` would be caught —
  relies on the existing `test_phase2f39_seed_role_guard.py` suite
  (unchanged, still passing) rather than a new 2F-39A-specific check.
