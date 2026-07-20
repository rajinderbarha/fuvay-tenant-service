# Manager Demo Account Review — Slice 2E

## Reviewed: manager@demo-ac-services.local (disabled in Slice 2D)

## Decision: keep disabled — demo environment does not require reactivation this slice

## Reasoning
Per Workstream 11's explicit branching: "if [the demo environment] does [require a manager persona]... reactivate only if explicitly supported by demo requirements." No such explicit requirement was found or asserted — the account's own history (zero logins, zero sessions, zero usage across its entire lifetime, per Slice 2D's investigation) provides no evidence anyone currently depends on a working manager demo account. Reactivating it would be introducing new functionality speculatively, not restoring something in active use.

Additionally, `manager-persona-implementation.md` found that a genuinely complete "manager" persona needs permission constants (team-wide job/quote/customer visibility) that either don't exist or weren't located this slice — reactivating this specific account now would only be able to demonstrate a partial manager (e.g., `P.STAFF_MANAGE` alone), which risks presenting an incomplete persona as if it were the real thing.

## What was verified instead
- Confirmed the account remains disabled (`is_active=false`, `role=staff`), unchanged from Slice 2D — no accidental reactivation occurred.
- Confirmed (via `tests/test_phase2d_tenant_access_model.py`'s existing `TestSeedScriptCanonicalGuard` tests, re-run this slice) that the seed script cannot recreate an invalid `tenant_manager` role for a future demo run — the Slice 2D fix remains in place and untouched.
- Confirmed via `test_get_current_user_now_populates_permission_overrides` that if a future slice does grant this (or any) staff account real manager permissions via `update_permissions`, they will actually take effect — the blocking issue Slice 2D identified is resolved.

## No audit evidence created this slice for this account
Since no state change was made (it remains exactly as Slice 2D left it), no new audit event was needed or created.
