# FINAL-L5-01E — Technician Authentication Flow Inventory

## Scope
Every component involved in Technician (`role: technician` / `staff`) authentication and the post-login redirect to `/staff/dashboard`, in `frontend/tenant-portal`.

## Components

| # | Path | Responsibility | Reads | Writes | Async deps | Redirect behavior | Duplicate responsibility |
|---|---|---|---|---|---|---|---|
| 1 | `app/staff/login/page.tsx` | Login form + submit handler | form state | `localStorage` (token, refresh, user_id, tenant_id, tenant_name, user_role) | `authApi.login()` | `router.push("/staff/dashboard")` on success (SPA nav, fixed in FINAL-L5-01D) | none |
| 2 | `lib/api.ts::authApi.login` | POST `/v1/auth/login` | — | — | fetch | — | none |
| 3 | `lib/api.ts::apiFetch` | Central fetch wrapper, injects Bearer token, handles 401→refresh→retry | `localStorage` token | `localStorage` token (on refresh) | fetch, `/v1/auth/token/refresh` | on unrecoverable 401: `clearSession()` → `window.location.href = "/login"` (**note: tenant-owner login, not `/staff/login`** — see Bug Fix Register L5-01E-002) | none |
| 4 | `hooks/useStaffContext.ts::useStaffContext` | Loads current user, verifies technician/staff role via live `/v1/auth/me` | `localStorage` token (via `getToken()`) | component state only | `authApi.me()` | none itself (StaffLayout acts on its result) | **was duplicated** (fixed this sprint — see below) |
| 5 | `hooks/useStaffContext.ts::StaffContextProvider` / `useStaffContextValue` | **New this sprint.** Shares the single `useStaffContext()` instance owned by `StaffLayout` with page content via React Context, so pages consume the resolved context instead of re-fetching | React Context | — | — | — | fixes #4 |
| 6 | `components/layout/StaffLayout.tsx` | Sole owner of the one `useStaffContext()` call; renders loading/sign-in/app shell based on its result; provides `ctx` to children via `StaffContextProvider` | `ctx` from `useStaffContext()` | — | `useStaffContext()` | none (renders inline states, not a redirect) — "Please sign in" / "staff only" screens are static, link to `/staff/login`, no auto-navigate | was duplicated with #7 before this sprint's fix |
| 7 | `app/staff/dashboard/page.tsx::StaffDashboardPage` | Route entry; renders `<StaffLayout><StaffDashboardContent/></StaffLayout>` | — | — | — | — | **fixed this sprint**: previously called `useStaffContext()` itself (2nd independent instance); now delegates entirely to `StaffLayout` and consumes via `useStaffContextValue()` |
| 8 | `app/staff/dashboard/page.tsx::StaffDashboardContent` | Dashboard body; 5 `useApi()` data fetches (skills, jobs, notifications, service areas, tenant status) | `useStaffContextValue()` | — | 5x `staffSelfApi`/`tenantSetupApi` calls | — | now only mounts once `StaffLayout` has already resolved auth (its data fetches no longer race the auth check) |
| 9 | *(none)* `middleware.ts` | — | — | — | — | — | **does not exist** for tenant-portal — confirmed via directory listing. There is no server-side route guard; `/staff/*` is guarded client-side only, by `StaffLayout`. This rules out a middleware-vs-client-guard conflict (Part 8) by construction. |
| 10 | `lib/authTimeline.ts` | **New this sprint.** Opt-in (`?authTimeline=1` or `localStorage.serviceos_auth_timeline=1`) timestamped console instrumentation for reproducing timing issues | — | — | — | — | none |

## Key finding this sprint
Components #4/#6/#7 previously had **two independent `useStaffContext()` instances** mounted concurrently on every `/staff/dashboard` load (one in `StaffLayout`, one in the page itself), each firing its own `/v1/auth/me` call and resolving through its own separate loading/error state machine. This directly violated mission rule 8 ("do not issue duplicate login/profile requests"). Fixed by making `StaffLayout` the sole owner and sharing its resolved context via `StaffContextProvider`/`useStaffContextValue()`. See Bug Fix Register L5-01E-001.

## What was ruled out
- **Middleware/client-guard conflict**: impossible — no middleware exists for this app.
- **Refresh-token race**: access tokens are minted with an 8-hour expiry (`ACCESS_TOKEN_EXPIRE_MINUTES=480`); a token used seconds after login cannot be near-expiry, so `apiFetch`'s 401→refresh path is not triggered on a fresh login.
- **JTI collision / blacklist false-positive**: JTIs are `uuid.uuid4()`, and the blacklist check fails open when Redis is unavailable (`app/dependencies/auth.py`) — no plausible source of a spurious 401 on a fresh token.
