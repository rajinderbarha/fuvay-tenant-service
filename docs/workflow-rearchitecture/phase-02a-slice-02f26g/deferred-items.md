# Deferred Items — Slice 2F-26G

| Item | Why deferred | Unblocked by |
|---|---|---|
| `DELETE /v1/webhooks/endpoints/{endpoint_id}` row | N09 gate failure | a passing fifth holdout |
| `DELETE /v1/geo/zones/{zone_id}` row | N09 gate failure | a passing fifth holdout |
| D-09 action-token repair (`bulk-disable`) | found by the fourth holdout; fixing and re-running it would be circular | a fifth frozen holdout |
| Token-based capability-action model | out of scope | a later tooling slice |
| Model-derived capability family | out of scope | a later tooling slice |
| Adjudication of the remaining 27 + 24 mixed-persona routes | explicitly out of scope | a validated classifier |
| All 28 security observations | no module selected; app changes forbidden | a slice that selects the module |
| Next authorization module selection | explicitly out of scope | approval of this gate |
