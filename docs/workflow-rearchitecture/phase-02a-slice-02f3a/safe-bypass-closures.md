# Safe Direct-Bypass Closure — Workstream 9

## The one candidate: accept/reject shadowing
Evaluated against the brief's 7-point test for whether a code change is
warranted:

1. **Two routes mutate the same record type?** YES — both load
   `ServiceJob` by the same `job_id`.
2. **They perform the same business transition?** YES — both accept/reject
   the job and update its status.
3. **They target the same acting persona?** YES — both are `staff`/
   `technician`-facing.
4. **One route has materially weaker authorization?** **NO in the
   exploitable sense** — `execution.home_service_router`'s copy is
   completely unreachable (Starlette's first-match-wins routing means it
   never executes; confirmed via a live HTTP call). A route that cannot be
   reached cannot be "weaker" in a way that matters for security, because
   it is never evaluated against a real request. (Its guard composition IS
   weaker on paper — see `authorization-comparison-matrix.csv` — but this
   is academic since the code path is dead.)

Since criterion 4 fails to establish a real, exploitable weakness (the
"weaker" route is not reachable at all), **the brief's threshold for a code
change is not met.** Per the explicit instruction: "If safe closure is not
proven, make no code change and mark the blocker" — however this isn't a
blocker either, since there is no live exposure. No code change was made.

## What WAS done instead
1. **Documented conclusively** (this directory + `canonical-route-disposition.csv`)
   which implementation is canonical and which is dead, with the exact live
   evidence (HTTP call, response shape, `engine_id`, error code) that
   proves it — so a future engineer does not need to re-derive this from
   scratch or guess.
2. **Added regression tests** (`test_phase2f3a_execution_assignment_overlap.py`)
   that lock in the current, correct routing precedence — if a future
   change to `app/main.py`'s import/registration order ever flips which
   implementation wins, these tests fail immediately with a clear message
   pointing back to this adjudication, rather than silently changing
   production behavior.
3. **Extended the inventory tool** (`--verify-overlap`) with an
   `ADJUDICATED_ROUTE_OVERLAPS` allowlist so any FUTURE overlap (not just
   this one) between these 3 modules is caught by CI/manual verification
   and forced through the same adjudication process, rather than silently
   accumulating more shadowed routes.

## What was explicitly NOT done, per the brief's prohibitions
- The shadowed `staff_accept_job`/`staff_reject_job` functions were **not
  deleted** — Workstream 9 explicitly prohibits removing routes based on
  this kind of finding alone, and a regression test
  (`test_execution_router_registers_before_shadow_is_confirmed_still_present_in_source`)
  actively guards against a future, unrelated cleanup accidentally deleting
  them without re-running this adjudication.
- No cross-pipeline adapter was added.
- No record identifier was rewritten.
- No status semantics were changed.
- No booking-creation behavior was touched.

## Other capabilities evaluated (not bypasses)
`provider_cancel_job` vs `cancel_assignment`, and all other capability
groups in `overlapping-capability-groups.csv`, were evaluated and found to
be **distinct, non-duplicate capabilities** (different transitions, in
several cases different record types touched even though both key off the
same `job_id`) — no bypass exists to close for any of them.
