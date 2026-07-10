# ServiceOS — Release Candidate: rc-1

**Date:** 2026-07-03
**Version:** serviceos-rc-1
**Backend:** rc-1 (config.py APP_VERSION)
**Migrations:** 048 migrations (000–048_sprint33_performance_indexes)
**API:** OpenAPI at /docs, /redoc, /openapi.json

---

## Included in rc-1

### Feature Sprints
- Sprints 1–29: All main feature engines (auth, tenants, booking, AI chat, payments, invoicing, reviews, complaints, notifications, analytics, marketing)
- Sprint 3: Admin Service Catalog + Tier Pricing
- Sprint 4: Tenant Onboarding + Provider Dashboard
- Sprint 5: Monetization Engine
- Sprints 8–12: Pricing Catalog, Provider Registration, Onboarding Checklist, Offering Enablement, Bookable/Visible Status
- Sprint 13: Marketing Launch Engine
- Sprint 14: Customer Category Flow Routing
- Sprints 15–19: AI Conversation Engine (DeepSeek), Home Service / Coaching / Real Estate chatbot flows, Booking Confirmation
- Sprints 20–23: Job Assignment, Execution Flow, Quote/Checklist, Invoice/Payment/Commission
- Sprints 24–25: Customer Reviews + Complaints/Disputes/Refund
- Sprint 26: Enterprise Filters + Data Grid
- Sprint 27: Notification + Chat + Audit Integration
- Sprint 28: Category Analytics + Reports
- Sprint 29: AI Hardening + Marketing Automation

### Platform Hardening
- District / Location / Server-Side Pagination Scalability Sprint
- Sprint 30: Full System Release Readiness Audit
- Sprint 31: Security + Tenant Isolation Hardening (TenantScopeService, CustomerScopeService, StaffScopeService)
- Sprint 32: End-to-End Production Smoke Testing (6 P1 fixes applied)
- Sprint 33: Performance + Load Testing (pagination caps, 6 composite indexes)
- Sprint 34: UI/UX Final Polish (Tailwind→design-tokens, route layouts, 0 TS errors)

### Sprint 35 (this sprint — Deployment + Release Candidate)
- `/v1/health` versioned alias added
- `/v1/ready` readiness endpoint added (returns 503 if DB or Redis down; blocks traffic with dev secrets in production)
- `nginx/nginx.conf` created (TLS termination + rate limiting)
- `next.config.js` created for both frontends (standalone output, NEXT_PUBLIC_API_URL, MOCK_MODE build guard)
- `app/config.py`: production fail-fast validator (refuses start with dev secrets / localhost DB)
- `DEBUG` default changed from `True` to `False`
- `.env.example` updated: all key names match config.py, missing vars added
- `monitoring/grafana/` provisioning stubs created
- `scripts/cron_jobs.sh` background job schedule documented
- `docs/DEPLOY.md` deployment runbook created

---

## Known Limitations in rc-1

1. **Staging deployment not yet verified** — requires actual cloud infrastructure with TLS certs and managed DB. See `docs/DEPLOY.md`.
2. **Nginx TLS cert** — `nginx/ssl/` directory is a placeholder; real certs must be provisioned (Let's Encrypt / cert manager).
3. **File storage** — Cloudinary config is optional; upload features return 503 gracefully if not configured.
4. **Mobile apps** (staff-app, customer-app) — React Native apps exist but are not included in this release. Web frontends (super-admin, tenant-portal) are included.
5. **Background jobs** — No containerised scheduler. Jobs must be run via cron on host or a separate worker container.
6. **REDIS_PASSWORD** — Production Redis password must be included in `REDIS_URL` string (`redis://:password@host:6379/0`). Separate `REDIS_PASSWORD` env var is used only by docker-compose postgres service, not config.py.
7. **Stripe** — `STRIPE_SECRET_KEY` in config but Stripe payment flow not yet implemented in business logic (placeholder for future sprint).

---

## Deployment Blockers Resolved in rc-1

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| B01 | P0 | nginx/nginx.conf missing — prod compose fails | Created nginx/nginx.conf |
| B02 | P0 | DEBUG defaults to True — prod risk | Changed default to False |
| B03 | P0 | Dev secrets allowed in production with no enforcement | model_validator fail-fast added to config.py |
| B04 | P0 | No NEXT_PUBLIC_API_URL config — falls back to localhost in prod | next.config.js created for both frontends |
| B05 | P1 | /v1/health and /v1/ready endpoints missing | Added to health_router.py |
| B06 | P1 | .env.example key name mismatches (JWT_SECRET_KEY missing, wrong names) | .env.example fully rewritten |
| B07 | P1 | MOCK_MODE login bypass not guarded for production builds | next.config.js build-time guard added |
| B08 | P1 | Grafana provisioning dirs missing — prod compose volume mount fails | monitoring/grafana/ stubs created |
| B09 | P2 | Background job schedule undocumented | scripts/cron_jobs.sh created |
| B10 | P2 | SENDGRID_API_KEY, STRIPE_SECRET_KEY not in .env.example | Added to .env.example |

---

## Build Artifacts

| Artifact | Value |
|---|---|
| Backend version | rc-1 |
| Frontend (tenant-portal) | rc-1 |
| Frontend (super-admin) | rc-1 |
| Migration head | 048_sprint33_performance_indexes |
| OpenAPI | /openapi.json |
| Docker image tag | rc-1 |

---

## Recommendation

**PARTIAL_READY_WITH_P1_DEPLOYMENT_FIX_LIST**

All P0 deployment blockers are resolved. Staging deployment requires provisioning
real infrastructure (managed DB, Redis, TLS certs, domain). Background jobs need
a scheduler. See Known Limitations above. No P0 blockers remain.
