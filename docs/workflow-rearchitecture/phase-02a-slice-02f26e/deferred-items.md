# Deferred Items — Slice 2F-26E

| Item | Why deferred | Unblocked by |
|---|---|---|
| `DELETE /v1/webhooks/endpoints/{endpoint_id}` canonical row | N09 gate failure | a passing fresh holdout |
| `DELETE /v1/geo/zones/{zone_id}` canonical row | N09 gate failure | a passing fresh holdout |
| Alias-blind parameter scan repair | found *by* the holdout; fixing and re-running it would be circular | a third frozen holdout |
| Actor-versus-scope conflation repair | same | a third frozen holdout |
| Capability-column taxonomy | out of this slice's scope | a later tooling slice |
| Adjudication of the remaining 75 mixed-persona routes | explicitly out of scope | a validated classifier |
| All 12 security observations | no module selected; app changes forbidden | a slice that selects the module |
| Next authorization module selection | explicitly out of scope | approval of this gate |
