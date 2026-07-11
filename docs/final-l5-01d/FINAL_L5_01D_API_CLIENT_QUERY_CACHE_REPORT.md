# FINAL-L5-01D — Central API Client and Query Cache Check

## Tenant Jobs
| Check | Status |
|---|---|
| Central client | Yes — `apiFetch` via `lib/api.ts`, no raw `fetch()` added in either migrated page |
| Typed API module | Yes — new `serviceJobsApi` (list/get), reused pre-existing `serviceJobAssignmentApi` |
| Canonical query keys | This app uses a simple `useApi`/`useAction` hook pattern (not a full query-cache library like React Query) — no query-key system to migrate; `useApi`'s `refetch()` is called explicitly after mutations |
| Correct invalidation after mutations | Yes — `job.refetch()` and `timeline.refetch()` called after assign/cancel/schedule actions |

## Customer Bookings
| Check | Status |
|---|---|
| Central client | Yes — unchanged, already used `apiFetch` |
| Typed API module | Pre-existing, unchanged this sprint (the fix was seed-side, not API-client-side) |
| Correct source contract | **Fixed this sprint** — the seed now populates the table the existing correct API contract already expected |
| Booking/tracking query keys | Same `useApi` pattern, no changes needed |

## Technician auth
| Check | Status |
|---|---|
| Canonical auth/session helper | Yes — `authApi.login()`/`authApi.me()`, unchanged |
| Canonical route guard | Yes — `useStaffContext()` hook, unchanged (already correctly implemented, re-verifies against live `/v1/auth/me` rather than trusting localStorage alone) |
| No duplicate token parser | Confirmed — single `getToken()` helper |
| No page-level raw fetch | Confirmed in the login page — only change was the redirect mechanism (`window.location.href` → `router.push()`), not the auth call itself |

## Result
All three affected flows use the central `apiFetch` client and typed domain modules — no raw fetch/URL-assembly was introduced by this sprint's fixes.
