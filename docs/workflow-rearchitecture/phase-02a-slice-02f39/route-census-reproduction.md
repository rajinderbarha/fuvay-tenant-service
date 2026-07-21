# Route Census Reproduction — Slice 2F-39

## Scope decision

This slice prioritized (1) fixing the concrete, evidenced seed-script
security gap and (2) resolving the 45 full-backend-regression failures
with real root-cause analysis, over (3) the ~261-route mounted-mutation
reclassification project. This was a deliberate scoping choice given the
session's effort budget: (1) and (2) were concrete, boundable, and fully
completable; (3) is, as Slice 2F-38 itself documented, comparable in size
to the entire 2F-35/36/37 program (a multi-day, route-by-route audit).

## What was reconfirmed (not re-derived from scratch)

- `verify_2f37.py`: 21/21 PASS, re-run fresh at the start and again at the
  end of this slice — the 313 canonical routes remain protected
  throughout every code change this slice made.
- The 313/313 canonical figure and the ~1,186-route auto-classified
  breakdown (`mounted-route-census.csv`, `mutation-disposition-census.md`
  from Slice 2F-38) were not independently re-run this slice — no
  application code affecting route mounting or guards changed (only test
  files and the two seed scripts), so there is no reason to expect the
  route census would differ from 2F-38's figures. This is stated as a
  reasoned inference, not as freshly-executed evidence — see
  `known-limitations.md`.

## What remains exactly as Slice 2F-38 left it

- 261 routes remain classifier-`UNVERIFIED`.
- ~77 of the 89 `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` routes remain
  un-spot-checked (12 were checked in 2F-38).
- No new canonical mutation was discovered or added this slice (Workstream
  4's "newly discovered mutation remediation" did not trigger, since no
  route classification work was performed to discover one).

## Certification impact

This is an **unresolved gap carried forward unchanged**, not a regression
and not newly discovered. It independently blocks
`CERTIFICATION_REMEDIATION_READY` per this slice's own quality gates
(#4/#5: "every mounted mutation route receives a final classification",
"no UNKNOWN route remains").
