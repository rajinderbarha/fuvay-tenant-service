# Risk-Scoring Model - Slice 2F-28

One model, applied to every module. Each dimension scored **0-3** with
evidence; no score assigned from route names alone.

## Risk dimensions (summed into `risk_sum`)

cross_tenant, identity_credential, permission_role_mgmt, financial_payment,
destructive_delete, bulk_operation, external_side_effect,
customer_data_privacy, audit_compliance, impersonation_session,
client_asserted_tenant, missing_object_ownership, service_layer_bypass,
internal_caller_exposure, read_privacy_linkage.

## Weighting dimensions (not part of risk_sum)

- `route_count` - risk-reduction leverage per slice, capped at 6 so a large
  low-risk module cannot outrank a small critical one.
- `impl_complexity`, `testability` - readiness signals.
- `product_blockers` - subtracted, because a module that cannot be closed
  without a product decision is not ready to select.

`priority_score = risk_sum + min(route_count, 6) - product_blockers`

## Ranking

| Module | risk_sum | routes | priority |
|---|---|---|---|
| M01_identity_credentials | 29 | 12 | **35** |
| M02_media_assets | 16 | 9 | 21 |
| M06_security_deposit | 19 | 3 | 20 |
| M03_enterprise_grid_views | 9 | 6 | 14 |
| M10_webhook_integration | 13 | 1 | 14 |
| M11_geo_zones | 11 | 1 | 12 |
| M04_profile_self_service | 7 | 4 | 11 |
| M05_marketing_automation | 7 | 3 | 9 |
| M07_provider_catalog_setup | 4 | 4 | 7 |
| M08_analytics_reports | 7 | 1 | 7 |
| M09_rag_knowledge | 7 | 1 | 7 |

M01 leads on **both** raw risk (29, next is 19) and priority (35), so the
selection does not depend on the route-count weighting.
