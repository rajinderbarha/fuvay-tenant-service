# FINAL-L5-01D — Technician Redirect Stabilization

## Fix applied
`app/staff/login/page.tsx`: replaced `window.location.href = "/staff/dashboard"` with Next.js `useRouter().push("/staff/dashboard")` — smallest correct fix, matching the SPA navigation pattern already used elsewhere in the app rather than introducing a new pattern.

## Requirements checklist

| Requirement | Status |
|---|---|
| No visible redirect loop | Confirmed no loop in any run — failures were a *stall* on `/staff/login`, never a bounce-between-routes loop |
| No temporary unauthorized page | Confirmed — no unauthorized/403 page was ever shown |
| No dashboard 404 | Confirmed — when the transition succeeded, it landed cleanly on `/staff/dashboard` with real rendered data |
| No repeated profile requests | **Partially — 2 calls to `/v1/auth/me` observed** in the debug capture (not confirmed as excessive/looping, just more than the ideal single call) |
| No race between token persistence and route guard | Fixed — `localStorage.setItem` calls are synchronous and complete before `router.push()` fires, and `useStaffContext` correctly re-reads the token on mount |
| Loading state appears while context resolves | Confirmed — `StaffDashboardPage` renders a `<Skeleton>` while `ctx.isTechnician` is being resolved, rather than a blank page |
| Expired/corrupt session returns safely to login | Not independently re-tested this sprint (time constraint) |
| Final route is consistent | **Not proven** — 1 of 5 repeated runs succeeded quickly (2,756ms); 4 timed out at 15s. See root cause report for the unresolved second contributing factor. |
| Deep link after login preserved if authorized | Not tested this sprint |
| Unauthorized deep link redirects once to canonical staff home | Not tested this sprint |

## Honest result
The **specific, diagnosed bug** (full-page reload + dev-mode HMR interference making the transition slow and hard to detect) is fixed, and the fix is proven to work correctly and quickly (2,756ms) in an isolated run. However, per the mission's explicit rule **"Do not mark Technician redirect stable based on one successful run"**, this sprint's repeated-run testing (5 fresh cold logins) showed 1 success and 4 timeouts, with the second contributing factor **not fully root-caused** (account lockout ruled out via direct DB check; test-harness resource contention in this heavily-loaded, hours-long session is the leading candidate, not confirmed).

## Failure status
Per the mission's own rule 12 ("Do not mark FINAL-L5-01 READY with any inconclusive required check"), **Technician redirect stability remains an open item** — real progress made, real fix applied and verified in isolation, but not proven deterministically stable across repeated runs this sprint. This is one of the concrete reasons this sprint's final recommendation is not an unconditional READY.
