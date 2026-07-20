# Deferred Items — Slice 2F-26H

| Item | Why deferred | Unblocked by |
|---|---|---|
| `DELETE /v1/webhooks/endpoints/{endpoint_id}` row | N09 gate failure | 100% independent validation by some route |
| `DELETE /v1/geo/zones/{zone_id}` row | N09 gate failure | 100% independent validation |
| `request_export` noun/verb boundary | found by the final holdout; the population is exhausted so it cannot be re-validated here | WS16 strategy 2/3 |
| `serviceability/check` persona boundary | same | WS16 strategy 2/3 |
| Adjudication of the remaining population | out of scope; classifier not fully validated | a chosen WS16 strategy |
| All security observations | no module selected; app changes forbidden | a slice that selects the module |
| Next authorization module selection | out of scope | approval of this gate |
