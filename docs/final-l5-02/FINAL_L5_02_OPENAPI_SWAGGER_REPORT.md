# FINAL-L5-02 — OpenAPI / Swagger Certification

Generated and validated the live OpenAPI 3.x spec (`openapi-certified.json`, 2,253 operations).

| Check | Result |
|---|---|
| Every mounted active endpoint appears | PASS — the spec IS the mounted route set (generated from the live app); 2,253 ops = all mounted routes |
| Operation IDs unique | **FAIL (minor)** — 7 duplicate operation IDs, all from the service-setup-template double-mount (see endpoint registry). FastAPI emits `UserWarning: Duplicate Operation ID` for each at startup. |
| Authentication scheme documented | PASS — `HTTPBearer` security scheme present; 2,134 of 2,253 ops carry a security requirement |
| Tags organized by domain | PASS — 254 tags, grouped by engine/domain |
| Invalid schema references | None detected — the spec generates without schema-resolution errors |
| No internal secret endpoint unintentionally public | 119 no-auth endpoints reviewed at the path level — all are expected public surfaces (login, health, public catalog, webhooks, signed-URL callbacks); no obviously-sensitive admin/finance path appears in the public set |

## Router-inventory vs OpenAPI comparison
- Router inventory: 137 mounted routers → OpenAPI: 2,253 endpoints. Consistent (the 6 unmounted routers contribute 0 endpoints, as expected).
- 0 unexplained missing active endpoints.
- **7 duplicate operation IDs** (the only non-clean result) — real, tied to the duplicate service-setup-template mount.
- 0 invalid schema references.

## Result
**OpenAPI certification: PASS with one documented defect** — the 7 duplicate operation IDs from the service-setup-template double-mount. This is a real cleanup item (removing the superseded Sprint 34F mount would resolve all 7), not a spec-corruption failure. The spec is otherwise complete, valid, and matches the mounted route set exactly.
