# Known Limitations — Slice 2F-38

See `final-known-limitation-registry.csv` for the structured registry.
Prose summary:

1. **Mounted route census incomplete.** 261 of 2,320 mounted routes remain
   classifier-`UNVERIFIED`; ~1,873 non-canonical mutation routes were not
   individually re-audited to the same depth as the 313 canonical set.
2. **Demo-account role data unresolved.** Both `manager@`/`readonly@demo-ac-services.local`
   remain `MANUAL_ROLE_CONFIRMATION_REQUIRED`.
3. **Migration 144 runtime unproven.** No PostgreSQL/Docker available.
4. **`workflow_service.py`'s `"tenant_manager"` static role-metadata
   fields** were not traced through to confirm they carry no executable
   authorization weight (see `canonical-role-certification.md`, "Third
   finding").
5. **N01 domain integrity** remains blocked (unchanged).
6. **Payments financial integrity** remains unproven (unchanged).
7. **Read-path privacy gaps** (pricing, item/location) remain open.
8. **Product-policy gaps** (Booking Exception Resolution, cancellation/
   rescheduling) remain unresolved.
9. **Full-backend regression determinism** — only run once this slice
   (not twice, given its ~12,096-test cost); see
   `full-backend-regression-report.md`.
10. **StaffPermission/cross-tenant/access-scope certification** rests on
    existing mocked-session tests, not live 2-tenant PostgreSQL runs.
