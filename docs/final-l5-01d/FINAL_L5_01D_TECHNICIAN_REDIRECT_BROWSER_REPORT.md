# FINAL-L5-01D — Real Chromium Technician Redirect Tests

## Method
5 fresh-browser-context cold logins as `tech1@demo-ac-services.local`, real Chromium, `waitForURL` assertion against `/staff/dashboard`.

## Results

| Metric | Value |
|---|---|
| Runs | 5 |
| Successful (URL reached within 15s) | 1 |
| Failed (timeout) | 4 |
| Fastest successful transition | 2,756ms (down from an unbounded/unreliable full-page-reload wait before this sprint's fix) |
| Unexpected intermediate routes | None — failures were a stall on `/staff/login`, never a wrong route or a loop |
| Account lockout ruled out | Confirmed via direct DB check: `failed_login_attempts=0`, `locked_until=NULL` for the test account after the run |

## Isolated verification (outside the 5-run batch)
A separate, isolated debug run (not part of the 5-run batch, run when the dev environment was less loaded) captured full console/network/pageerror events and confirmed: real `200` login, real `/v1/auth/me` resolution, and a full landing on `/staff/dashboard` with genuine rendered data ("Welcome back, Technician One", real assigned-job stats). This proves the fixed code path is **correct** when it completes.

## Honest result
**Not proven deterministically stable across repeated runs.** The fix (SPA router instead of full-page reload) is real, correct, and measurably faster when successful, but the 5-run batch's 4 timeouts were not fully root-caused this sprint (account lockout ruled out; test-harness resource contention in this very long, heavily-loaded session is the leading unconfirmed candidate — see root-cause report). Per the mission's explicit rule against certifying stability from one successful run, this check remains **open**.
