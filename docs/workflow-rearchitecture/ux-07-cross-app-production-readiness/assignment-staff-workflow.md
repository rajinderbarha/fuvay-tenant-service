# Assignment/Staff Workflow (Workstream 6)

Covered live this round as part of the Workstream 19 E2E proof: real
`GET /v1/provider/service-jobs/{id}/eligible-staff` (same-tenant filter
confirmed via `match_reasons`) and real
`POST /v1/provider/service-jobs/{id}/assign` against a real technician
account, both exercised against the same real job created in the E2E proof.
See `live-e2e-evidence.md` step 10 and `api-contract-audit.csv`.

Not attempted this round: negative-path testing (e.g. attempting to assign
a cross-tenant staff member, or reassignment/cancel-assignment flows) —
deferred to a later round.
