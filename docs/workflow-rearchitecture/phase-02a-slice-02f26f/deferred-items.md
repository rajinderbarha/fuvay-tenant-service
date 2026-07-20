# Deferred Items — Slice 2F-26F

| Item | Why deferred | Unblocked by |
|---|---|---|
| `DELETE /v1/webhooks/endpoints/{endpoint_id}` row | N09 gate failure | a passing fourth holdout |
| `DELETE /v1/geo/zones/{zone_id}` row | N09 gate failure | a passing fourth holdout |
| Capability-family prefix reordering | found by the third holdout; fixing and re-running it would be circular | a fourth frozen holdout |
| Write-pattern equality exclusion | same | a fourth frozen holdout |
| Model-derived capability family | out of scope | a later tooling slice |
| Adjudication of the remaining 51 + 24 mixed-persona routes | explicitly out of scope | a validated classifier |
| All 20 security observations | no module selected; app changes forbidden | a slice that selects the module |
| Next authorization module selection | explicitly out of scope | approval of this gate |
