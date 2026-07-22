# Frontend Access Representation — Slice 2E

## Status: no frontend changes made this slice

## Why
Workstream 9 asks to align existing permission-aware navigation with "effective permissions" for the manager and read-only personas. Neither persona reached a state where aligning the frontend would be meaningful this slice:
- **Manager**: the mechanism works, but no real manager permission configuration was applied to any account (see `manager-persona-implementation.md`) — there is nothing concrete for the frontend to reflect yet.
- **Read-only**: correctly BLOCKED at the backend (see `tenant-readonly-implementation.md`) — per rule 8 ("do not make frontend navigation the security boundary") and the general principle throughout this series that backend must be authoritative before frontend represents it, building a "read-only" frontend indicator ahead of a backend that cannot actually enforce read-only access would create exactly the false-safety appearance this series has repeatedly guarded against (e.g. Slice 1's "no fake success states" rule, Slice 2's "no fake zero counts" rule).

## What already exists and remains correct, unchanged
`usePermissions()` (super-admin, confirmed Slice 2) already fetches real permissions from `GET /v1/auth/me` and drives nav visibility — this pattern, once a real manager/read-only account exists with a working backend model, is the correct existing mechanism to extend. No new pattern needs to be invented.

## Recommendation for when personas are unblocked
Once a manager persona has a concrete permission set applied to a real account, and once read-only enforcement covers all supported tenant mutation routes, the frontend work is a matter of: (1) ensuring `GET /v1/auth/me` returns the account's actual effective permissions (already does, since it presumably reads from the same JWT/DB path — not independently re-verified this slice), and (2) using existing `usePermissions()`-style filtering in the tenant-portal app (which does not yet have this hook — confirmed absent in Slice 2/2B's tenant-portal audits) to hide/disable mutation UI for a read-only user, backed by the now-comprehensive backend guard.
