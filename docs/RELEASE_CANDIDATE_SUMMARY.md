# ServiceOS — Release Candidate rc-1 Summary

**Date:** 2026-07-03
**Version:** serviceos-rc-1
**Backend version string:** `rc-1` (app/config.py APP_VERSION)
**Migration head:** `048_sprint33_performance_indexes`
**Test count:** 2681 passing, 0 failing

---

## What's in rc-1

### Backend (FastAPI + PostgreSQL + Redis)
- 54 engine directories under `app/engines/`
- 49 Alembic migrations (001–048)
- 39 routers registered in `app/main.py`
- Full async stack: asyncpg + SQLAlchemy 2.x + Redis async

### API Coverage
- **Auth:** JWT login/refresh/logout, role-based (super_admin, tenant_owner, provider, customer)
- **Admin:** Tenant CRUD, engine management, service catalog, pricing, analytics, marketing
- **Provider:** Registration, onboarding checklist, offering enablement, job execution, invoicing, reviews
- **Customer:** Booking flows (home service, coaching, real estate), AI chatbot, payments, complaints
- **Public:** Self-registration with OTP + Razorpay payment flow

### AI / Chatbot
- DeepSeek orchestrator with 7 tools (get_service_catalog, get_available_slots, get_my_bookings, get_booking_detail, get_active_job, get_price_estimate + extras)
- Category-specific flows: Home Service, Coaching/IELTS, Real Estate
- Booking confirmation creates final records in DB; slot holds expire via background job

### Frontend
- **super-admin portal:** Next.js 16 (149 total pages across both portals)
- **tenant-portal:** Next.js 16, route-level layout, design-token CSS vars, 0 TS errors
- Both portals have `next.config.js` with standalone output, API URL config, MOCK_MODE build guard

### Security
- TenantScopeService / CustomerScopeService / StaffScopeService on all routes
- Production fail-fast: config.py rejects start with dev secrets when APP_ENV=production
- PII masking in structlog, OWASP headers middleware, rate limiting, idempotency middleware
- CORS: wildcard blocked in production by config validator

### Deployment
- `Dockerfile` multi-stage, non-root user, HEALTHCHECK
- `docker-compose.yml` (dev), `docker-compose.prod.yml` (prod with nginx + prometheus + grafana)
- `nginx/nginx.conf` TLS reverse proxy, rate limiting, /metrics restricted to internal
- `.env.example` complete; `docs/DEPLOY.md` full runbook
- `/health`, `/v1/health`, `/v1/ready` endpoints

---

## Known Limitations

| # | Limitation | Impact |
|---|-----------|--------|
| L1 | Staging infra not yet provisioned | Must provision before production |
| L2 | nginx/ssl/ TLS certs are placeholders | Must use real certs in production |
| L3 | Stripe payment flow config-only | Future sprint |
| L4 | Background jobs need host cron | No containerised scheduler yet |
| L5 | Mobile apps (staff-app, customer-app) excluded from web release | React Native apps exist in repo |
| L6 | E2E Playwright tests require live servers | Structural validation passes; browser tests pending |

---

## Files Created in Sprint 35 (Deployment Sprint)

| File | Purpose |
|------|---------|
| `nginx/nginx.conf` | TLS reverse proxy, rate limiting, metrics isolation |
| `frontend/tenant-portal/next.config.js` | Standalone output, API URL, MOCK_MODE guard |
| `frontend/super-admin/next.config.js` | Same |
| `app/engines/health_router.py` (updated) | Added /v1/health + /v1/ready |
| `app/config.py` (updated) | Production fail-fast validator, DEBUG=False default |
| `.env.example` (rewritten) | All key names match config.py exactly |
| `monitoring/grafana/datasources/prometheus.yml` | Grafana provisioning stub |
| `monitoring/grafana/dashboards/dashboard.yml` | Grafana dashboard provisioning stub |
| `scripts/cron_jobs.sh` | Background job cron schedule |
| `docs/DEPLOY.md` | Full deployment runbook |
| `docs/RELEASE_NOTES_rc1.md` | Release notes |

---

## Quick Verification Commands

```bash
# Run full test suite (2681 tests)
python -m pytest tests/ -q

# Check health
curl http://localhost:8000/health
curl http://localhost:8000/v1/ready

# Check migration head
alembic current

# TypeScript check — tenant-portal
cd frontend/tenant-portal && npx tsc --noEmit

# TypeScript check — super-admin
cd frontend/super-admin && npx tsc --noEmit
```
