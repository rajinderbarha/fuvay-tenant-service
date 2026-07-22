# Targeted Test Report (WS13)

`tests/test_phase2f35_critical_authorization_batch.py` — 34 tests across
9 classes:

- `TestScopeGuardsLive` (1) — all 11 routes access-scope gated, live
- `TestWebhookTenantAuthority` (3)
- `TestRagTenantAuthority` (7)
- `TestSecurityTenantAuthority` (4)
- `TestDocumentTenantAuthority` (5)
- `TestNonOracularResponses` (2)
- `TestNoBypassOfClosedRoutes` (4)
- `TestSetBAdjudication` (2)
- `TestCanonicalClosure` (3)
- `TestM01N01GeoNonRegression` (3)

**Result: 34/34 passed.**

Every category the mission required (authorization, tenant/object,
service, security/privacy, held adjudication, coverage arithmetic,
cross-module non-regression) has at least one positive assertion;
negative controls are explicit in `TestNonOracularResponses` and the
`TestNoBypassOfClosedRoutes` class (each fails if a closure is weakened,
an alternate route reappears, or an internal caller loses its trusted
context).
