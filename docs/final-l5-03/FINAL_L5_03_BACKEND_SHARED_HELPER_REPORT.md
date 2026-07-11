# FINAL-L5-03 — Backend Shared Helper Audit

## Audited (read directly this sprint)
- `app/dependencies/auth.py::get_current_user` — stateless JWT decode + Redis blacklist check (fails open on Redis unavailability), single implementation, used via `Depends()` across the whole backend. No per-router reimplementation found.
- `require_super_admin`/`require_tenant_owner`/`require_staff_or_above`/`require_customer`/`require_technician` — all layer on top of the same `get_current_user`, consistent shape, all call `_check_force_password_change` first. No divergent tenant-scope-check logic found across the routers touched by this sprint's fixes.
- `app/middleware.py::register_middleware` — `RequestIDMiddleware`, `StructuredLoggingMiddleware`, `UsageQuotaMiddleware`, `IdempotencyMiddleware`, `CORSMiddleware`, `SecurityHeadersMiddleware`, applied via `add_middleware()` in a fixed order.
- `register_exception_handlers` (`app/exceptions.py`) — centralized error-envelope construction, referenced from `main.py`.

## Real, significant finding: 500 responses are missing CORS headers
Live-verified this sprint: `GET /v1/provider/wallet` (before the frontend fix routed callers away from it) returned `HTTP 500` with **no `Access-Control-Allow-Origin` header**, which the browser reports as a CORS failure rather than surfacing the real error — see Error Handling Standard for the full symptom description. Root cause is very likely `CORSMiddleware`'s position in the ASGI middleware stack relative to where unhandled exceptions get converted to responses (`add_middleware()` calls in `register_middleware()` are applied in the order `SecurityHeaders, CORS, Idempotency, UsageQuota, StructuredLogging, RequestID` — Starlette's `add_middleware` prepends, so the **last**-added middleware, `RequestIDMiddleware`, is actually the **outermost** layer, with `CORSMiddleware` several layers *inside* it, not outermost as CORS middleware conventionally should be).

### Why this was not blind-fixed this sprint
Middleware ordering is security-sensitive, cross-cutting infrastructure — reordering it affects **every single endpoint in the backend**, not just the one that surfaced the symptom. A wrong reordering could:
- Silently change what headers are visible to which layer (e.g. if `SecurityHeadersMiddleware` depends on running before/after CORS for a reason not documented here).
- Interact unpredictably with `IdempotencyMiddleware`'s response-caching logic (it reads/writes headers on the response).
- Require a full regression pass across all ~2,253 previously-inventoried endpoints (FINAL-L5-02) to be confident nothing broke — which is a full-sprint-scale verification effort on its own, not something to attempt inside an already-large cleanup sprint without dedicated time.

Per rule 1 ("do not rewrite the entire project without evidence") and "consolidate only where safe and test-covered" (Part 23's own instruction), this is correctly scoped as a **documented, real, prioritized finding** rather than an attempted fix — logged in Remaining Blockers and the Deprecation Register for a dedicated, properly-tested follow-up.

## Known risks checked, not found present
- Read-only requests reaching 422 instead of 403: re-confirmed still correct (403-before-422 pattern proven in FINAL-L5-01D, unaffected by this sprint's frontend-only changes).
- Different tenant-scope checks across routers: not found divergent in the routers this sprint's fixes touched (`invoice_payment/provider_router.py`, `home_service_assignment/*` — all use the same `get_current_user` + `str(user.tenant_id)` pattern).
- Endpoints returning incompatible error shapes: the embedded-not-found pattern (HTTP 200 + `success:false`) is a known, carried, documented low-severity finding from FINAL-L5-01D/02B, unchanged this sprint.

## Result
No backend consolidation was unsafe or untested this sprint because none was attempted beyond what the frontend fixes required (zero backend Python files modified). The one real, significant backend architectural finding (CORS-header-on-error gap) is documented with full reasoning for why it wasn't attempted blind, consistent with the mission's own safety rules.
