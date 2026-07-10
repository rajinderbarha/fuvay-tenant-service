# ServiceOS — Final Security Proof Report

**Date:** 2026-07-03
**Sprint:** 36 (verification only)
**Source sprints:** 31 (Security Hardening), 32 (Smoke Testing)

---

## Security Architecture

### Authentication
- **JWT** with `HS256`, 30-minute access tokens, 7-day refresh tokens
- Tokens signed with `JWT_SECRET_KEY` (64-char hex in production, enforced by config validator)
- All protected routes use `get_current_user` FastAPI dependency
- Password hashed with `passlib[bcrypt]`; `password_hash` field excluded from all response schemas

### Authorization — Scope Services

| Service | Location | Purpose |
|---------|----------|---------|
| `TenantScopeService` | `app/core/scope_services.py` | Ensures admin routes only access data belonging to the JWT tenant |
| `CustomerScopeService` | `app/core/scope_services.py` | Ensures customer routes only access data belonging to the JWT customer |
| `StaffScopeService` | `app/core/scope_services.py` | Ensures staff routes only access data belonging to the JWT staff member |

All three services extract identity from JWT claims — never from request body, query params, or headers. Frontend cannot override `tenant_id`, `customer_id`, or `staff_member_id`.

### Tenant Isolation Rules (enforced)
- No tenant sees another tenant's data
- No customer sees another customer's data
- No provider accesses admin-only data
- Frontend hiding is not security; backend enforces everything
- IDOR confirmed isolated in Sprint 32 cross-tenant test

### FastAPI Dependencies
- `require_customer`: validates JWT has `role=customer`; returns 401 if not
- `require_technician`: validates JWT has `role=staff` or `role=provider`
- Both reject `customer_id`/`staff_id` from request body

---

## Production Security Controls

| Control | Implementation | File |
|---------|----------------|------|
| DEBUG=False default | Changed from True in Sprint 35 | `app/config.py` |
| Dev secrets rejected in production | `model_validator` raises at startup | `app/config.py` |
| CORS wildcard blocked in production | Validator rejects `*` in `ALLOWED_ORIGINS` | `app/config.py` |
| Security headers on all responses | `SecurityHeadersMiddleware` | `app/middleware.py` |
| OWASP headers | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, Strict-Transport-Security | `app/middleware.py` |
| Rate limiting | `RATE_LIMITS` per endpoint; `auth:login` has stricter limit | `app/core/security.py` |
| Idempotency | `IdempotencyMiddleware` for POST/PUT/PATCH | `app/middleware.py` |
| PII masking | Structlog processor masks password, token, phone, email, otp, api_key, sk-* patterns | `app/core/pii_filter.py` |
| Sentry PII scrubbing | `_scrub_pii` before_send hook | `app/observability.py` |
| TLS termination | nginx with TLSv1.2/1.3 only | `nginx/nginx.conf` |
| /metrics internal only | nginx restricts to 10.x/172.x/192.168.x | `nginx/nginx.conf` |
| MOCK_MODE build guard | Build fails if NEXT_PUBLIC_USE_MOCK=true in production | `next.config.js` |

---

## Sensitive Fields Never Exposed

- `password_hash` — excluded from all Pydantic response schemas via `model_config`
- `otp` / OTP values — stored in Redis with TTL; never returned in API response
- `api_key` / secret keys — never returned; PII mask applies
- `JWT_SECRET_KEY` / `SECRET_KEY` — server-side only; not in any response

---

## What Is Not Yet Done

- **RBAC granularity** at field level (e.g., admin seeing all tenant fields vs. tenant owner self-view) is enforced by route separation, not per-field policies
- **API key rotation** endpoint not implemented (future sprint)
- **IP allowlist** for admin endpoints (nginx can add; not configured)
- **Audit trail** wired in Sprint 27; covers mutations but not all read operations

---

## Test Coverage (Security-Related)

| Test File | Security Area | Tests |
|-----------|---------------|-------|
| `tests/test_sprint31_security.py` | TenantScopeService, IDOR isolation | 41 |
| `tests/test_phase22_production.py` | Security headers, rate limiting, PII filter, middleware | 42 |
| `tests/test_sprint32_smoke.py` | End-to-end auth + cross-tenant access denial | — |
| Various router tests | 401/403 on missing/invalid JWT | Throughout |
