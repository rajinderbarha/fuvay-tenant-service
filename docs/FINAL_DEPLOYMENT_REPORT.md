# ServiceOS — Final Deployment Report

**Date:** 2026-07-03
**Sprint:** 35 (Deployment Sprint) + 36 (Verification)
**Release:** serviceos-rc-1

---

## Deployment Artifacts Inventory

| Artifact | Status | Notes |
|----------|--------|-------|
| `Dockerfile` | EXISTS | Multi-stage, non-root user, HEALTHCHECK |
| `docker-compose.yml` | EXISTS | Dev: postgres, redis, api |
| `docker-compose.prod.yml` | EXISTS | Prod: + nginx, prometheus, grafana |
| `nginx/nginx.conf` | EXISTS | TLS, rate limiting, /metrics internal |
| `nginx/ssl/` | PLACEHOLDER | Needs real Let's Encrypt certs |
| `.env.example` | EXISTS | All 30+ vars documented, match config.py |
| `app/config.py` | EXISTS | Production fail-fast validator, DEBUG=False |
| `frontend/tenant-portal/next.config.js` | EXISTS | Standalone output, API URL, MOCK guard |
| `frontend/super-admin/next.config.js` | EXISTS | Same |
| `monitoring/grafana/datasources/prometheus.yml` | EXISTS | Provisioning stub |
| `monitoring/grafana/dashboards/dashboard.yml` | EXISTS | Provisioning stub |
| `scripts/cron_jobs.sh` | EXISTS | Background job cron schedule |
| `docs/DEPLOY.md` | EXISTS | Full deployment runbook |
| `alembic/` | EXISTS | 49 migrations, 000–048 |

---

## Health Endpoints

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `GET /health` | Load-balancer heartbeat | `{status: "ok" | "degraded", checks: {...}}` |
| `GET /v1/health` | Versioned alias | Same as /health |
| `GET /v1/ready` | Readiness gate | 200 `{ready: true}` or 503 `{ready: false, reason: ...}` |

The `/v1/ready` endpoint returns 503 if:
- Database is unreachable
- Redis is unreachable
- `APP_ENV=production` and dev secrets detected in environment

---

## Production Config Requirements

Variables that MUST be set before `APP_ENV=production` (enforced by `model_validator`):

| Variable | Requirement |
|---------|------------|
| `SECRET_KEY` | Must not contain "dev-secret-key" |
| `JWT_SECRET_KEY` | Must not contain "dev-jwt-secret" |
| `DATABASE_URL` | Must not point to localhost |
| `ALLOWED_ORIGINS` | Must not contain "*" |

Failure to set these causes the API to **refuse to start** — it raises `ValueError` at import time.

---

## Deployment Steps (Summary)

```bash
# 1. Configure
cp .env.example .env.production
# Edit: APP_ENV=production, real secrets, real DATABASE_URL

# 2. Build
docker build -t serviceos-api:rc-1 .

# 3. Migrate
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head

# 4. Seed (once)
docker compose -f docker-compose.prod.yml run --rm api python scripts/seed_demo_users.py

# 5. Start
docker compose -f docker-compose.prod.yml up -d

# 6. Verify
curl https://yourdomain.com/health
curl https://yourdomain.com/v1/ready
```

Full runbook: `docs/DEPLOY.md`

---

## Rollback Plan

1. **API:** Change image tag in compose → `docker compose -f docker-compose.prod.yml up -d api`
2. **Migration:** `alembic downgrade -1` (test on staging first; some migrations are irreversible)
3. **Frontend:** Re-deploy previous Next.js build from previous git tag
4. **Database:** Restore from pg_dump backup taken before migration

---

## Background Jobs

| Job | Schedule | Command |
|-----|----------|---------|
| Notification dispatch | Every 1 min | `python -m app.jobs.notifications dispatch` |
| Notification retry | Every 5 min | `python -m app.jobs.notifications retry` |
| Notification cleanup | Hourly | `python -m app.jobs.notifications cleanup` |
| Draft/slot-hold expiry | Every 15 min | `python -m app.jobs.expire_drafts` |

All jobs are idempotent and safe to run more frequently.

---

## Remaining Deployment Work

| Item | Type | Priority |
|------|------|---------|
| Provision staging managed DB + Redis | Infrastructure | P0 for staging |
| Obtain TLS certificates (Let's Encrypt) | Infrastructure | P0 for staging |
| Configure actual domain DNS | Infrastructure | P0 for staging |
| Replace Grafana stubs with real dashboards | Monitoring | P2 |
| Containerise background jobs | DevOps | P2 |
| Stripe live keys + payment flow | Feature | Future sprint |
