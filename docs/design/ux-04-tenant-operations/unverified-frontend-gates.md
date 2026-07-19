# Unverified Frontend Gates

Gates that exist as typed contracts (`ActionPermissionView`,
`Ux04OperationsAdapter`) but are NOT wired to any real backend
authorization check this phase — every "available"/"reason" value in
`lib/ux04/fixtures.ts` is a design-time fixture, not a live permission
evaluation:

- Parts-request approve/reject gating (`inventory:items:approve`) —
  presentation-only; real gating must come from `StaffPermission` rows via
  a real API contract.
- Job status transition allowed-next list — presentation-only; the real
  set of allowed transitions must come from the backend's actual state
  machine, not be inferred client-side.
- Assignment/reassign/unassign reason-required flag — presentation-only.
- Command Center queue item actions — presentation-only.

None of these should be treated as an authorization boundary — see
`app/core/permissions.py` and `StaffPermission` for the real source of
truth once a backend contract is confirmed (`backend-contract-dependencies.csv`).
