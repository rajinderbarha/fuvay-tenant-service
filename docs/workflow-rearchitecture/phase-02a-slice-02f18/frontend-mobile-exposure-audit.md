# Frontend/Mobile Exposure Audit

## Callers found
| App | Path group | Read/Mutation | Screen |
|---|---|---|---|
| `frontend/tenant-portal` (`lib/api.ts`) | `/v1/provider/notifications*` | both | provider notification bell/center |
| `frontend/tenant-portal` | `/v1/provider/chat*` | both | provider chat/messaging screens |
| `frontend/tenant-portal` (`app/staff/chat/page.tsx`) | `/v1/staff/chat*` | both | tenant-portal's staff chat screen |
| `frontend/tenant-portal` | `/v1/staff/notifications*` | both | wired in `lib/api.ts` |
| `mobile/staff-app` (`src/lib/api.ts`) | `/v1/staff/chat*` | both | staff chat screens |
| `mobile/staff-app` (`src/screens/NotificationsScreen.tsx`) | `/v1/staff/notifications*` | both | notifications screen |
| — | `/v1/provider/audit-logs*` | — | **FRONTEND_MUTATION_SURFACE_ABSENT** — no caller in any frontend/mobile app |

`frontend/customer-app`, `mobile/customer-app`, `frontend/super-admin`: no
matches for any of the 5 path groups.

## Requirement checks
- Customer recipients cannot be arbitrarily searched/selected from any
  provider UI reaching this router — no such search endpoint exists on this
  router (`recipient-authority.md`).
- Provider-internal conversations are not exposed to customer apps — no
  `/v1/provider/*` or `/v1/staff/*` call exists in `customer-app`.
  Read-only actors: the frontend cannot enforce backend authorization; the
  router-level `require_owner_or_office_staff_mutation` fix in this slice
  is the actual enforcement point regardless of what the UI shows.
- Technicians see the same staff chat/notification screens as staff in the
  current UI — no frontend distinction between assigned/unassigned jobs
  exists either (consistent with the backend's tenant-wide policy
  documented in `staff-technician-communication-policy.md`).
- Backend remains authoritative — this slice changed only backend
  dependencies; no frontend file was modified.
- No broadcast control is exposed anywhere (matches
  `bulk-broadcast-safety.md`'s finding that no such capability exists).

## No frontend/mobile code changed this slice
Per the mission's "make only minimal policy/state corrections, do not
redesign pages" and this router's fix requiring no frontend contract
change (guard rejects unauthorized callers with a 403, which existing error
handling in these apps already surfaces as a generic auth error) — no
frontend or mobile file needed modification.
