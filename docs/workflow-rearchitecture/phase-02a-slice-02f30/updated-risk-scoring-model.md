# Updated Risk-Scoring Model - Slice 2F-30

Recomputed from scratch after M01 closure. 13 risk dimensions scored 0-3, each
backed by reading the router **and** the service - never by route name.

`priority_score = risk_sum + min(canonical_routes, 6) - product_blockers
                  - (1 if held_uncertainty >= 3 else 0)`

Route count is capped at 6 so a large low-risk module cannot outrank a small
critical one; blockers and held uncertainty are penalties because an
unadjudicated or policy-blocked module is not ready to implement.

## Evidence discipline applied

The `ownership_verified_in_service` column records, per module, what the
service actually does. Two first-pass scores were corrected downward after
reading the code (media, security deposit) and two were confirmed severe
(geo: no tenant predicate; webhook: client-asserted tenant only). A score
without that column is not evidence.

## Full ranking

| Module | risk | routes | held | blockers | priority |
|---|---|---|---|---|---|
| N09_webhook_integration | 13 | 1 | 0 | 0 | 14 |
| N01_media_assets | 10 | 9 | 3 | 1 | 14 |
| N02_enterprise_grid_views | 8 | 6 | 0 | 1 | 13 |
| N10_geo_zones | 11 | 1 | 2 | 0 | 12 |
| N05_security_deposit | 10 | 3 | 4 | 2 | 10 |
| N03_profile_self_service | 6 | 4 | 0 | 0 | 10 |
| N04_marketing_automation | 7 | 3 | 0 | 1 | 9 |
| N06_provider_catalog_setup | 4 | 4 | 2 | 1 | 7 |
| N07_analytics_reports | 6 | 1 | 0 | 1 | 6 |
| N08_rag_knowledge | 6 | 1 | 4 | 1 | 5 |
