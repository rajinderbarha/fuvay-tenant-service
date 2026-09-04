# Fuvay — Deployment Runbook

## Release Candidate: serviceos-rc-1

---

## Quick Start (Docker Compose — Staging)

```bash
# 1. Clone & configure
git clone https://github.com/YOUR_ORG/serviceos.git
cd serviceos
cp .env.example .env
# Edit .env — set APP_ENV=staging, real DATABASE_URL, JWT_SECRET_KEY, SECRET_KEY

# 2. Build image
docker build -t serviceos-api:rc-1 .

# 3. Start infrastructure
docker compose -f docker-compose.yml up -d postgres redis
# Wait for healthy:
docker compose ps

# 4. Run migrations (from zero — creates all 48 tables + indexes)
docker compose run --rm api alembic upgrade head

# 4b. Seed the master catalog (REQUIRED on every environment, not staging-only —
# migrations only create schema; without this, service_categories has zero
# rows and every tenant's Services & Pricing setup fails with
# "No Home Services category is configured." All idempotent, safe to re-run.
docker compose run --rm api python scripts/seed_universal_categories.py
docker compose run --rm api python scripts/seed_service_groups.py
docker compose run --rm api python scripts/seed_master_services.py
docker compose run --rm api python scripts/seed_brands.py
docker compose run --rm api python scripts/seed_issue_types.py
docker compose run --rm api python scripts/seed_checklists.py

# 5. Seed demo users (staging only)
docker compose run --rm api python scripts/seed_demo_users.py

# 6. Start API
docker compose up -d api

# 7. Verify
curl http://localhost:8000/health
curl http://localhost:8000/v1/ready
open http://localhost:8000/docs
```

---

## Production Deployment (docker-compose.prod.yml)

### Prerequisites
- TLS certificates at `./nginx/ssl/fullchain.pem` and `./nginx/ssl/privkey.pem`
- `.env.production` with production secrets (see `.env.example`)
- Bot-booking deployment gate completed (see
  [`deployment/bot-booking-protection.md`](deployment/bot-booking-protection.md))
- Docker + Docker Compose v2 on the host
- Managed PostgreSQL + Redis recommended (or use compose services)

### Steps

```bash
# 1. Configure
cp .env.example .env.production
# Edit .env.production:
#   APP_ENV=production
#   SECRET_KEY=<64-char random hex>
#   JWT_SECRET_KEY=<64-char random hex>
#   DATABASE_URL=postgresql+asyncpg://user:pass@managed-db-host:5432/serviceos
#   REDIS_URL=redis://:password@managed-redis-host:6379/0
#   ALLOWED_ORIGINS=https://admin.yourdomain.com,https://portal.yourdomain.com
#   DEEPSEEK_API_KEY=<real key>
#   CLOUDINARY_CLOUD_NAME=<your cloud>
#   CLOUDINARY_API_KEY=<your key>
#   CLOUDINARY_API_SECRET=<your secret>

# Edit nginx/nginx.conf: replace YOUR_DOMAIN with your real domain

# 2. Pull / build image
docker compose -f docker-compose.prod.yml pull api
# Or build locally:
docker build -t ghcr.io/YOUR_ORG/serviceos/serviceos-api:rc-1 .
docker push ghcr.io/YOUR_ORG/serviceos/serviceos-api:rc-1

# 3. Run migrations (ALWAYS before starting app)
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head

# 4. Start all services (one API container, four Uvicorn workers)
docker compose -f docker-compose.prod.yml up -d

# 5. Verify health
curl https://yourdomain.com/health
curl https://yourdomain.com/v1/ready

# 6. Set up background jobs (on the host or in a separate worker container)
# See: scripts/cron_jobs.sh
```

### Production Minimal Seed (run once)

```bash
# Creates: super_admin user, system defaults, engine registry, categories
docker compose -f docker-compose.prod.yml run --rm api \
  python scripts/seed_demo_users.py
# Idempotent — safe to re-run. Creates admin@serviceos.in if not exists.
```

---

## Environment Variable Matrix

| Variable | Required | Default | Notes |
|---|---|---|---|
| `APP_ENV` | Yes | `development` | Must be `production` in prod |
| `SECRET_KEY` | Yes | dev placeholder | 64-char hex; app refuses to start in prod if placeholder |
| `JWT_SECRET_KEY` | Yes | dev placeholder | 64-char hex; same enforcement |
| `DATABASE_URL` | Yes | localhost dev | Full asyncpg connection string |
| `DATABASE_POOL_SIZE` | Yes | `10` in prod compose | Per-worker persistent DB connections |
| `DATABASE_MAX_OVERFLOW` | Yes | `5` in prod compose | Per-worker burst DB connections |
| `DATABASE_POOL_TIMEOUT` | Optional | `30` | Seconds to wait for a pooled connection |
| `DATABASE_IDLE_IN_TRANSACTION_TIMEOUT_SECONDS` | Optional | `60` | PostgreSQL safety cutoff for interrupted transactions |
| `REDIS_URL` | Yes | localhost dev | Include password if auth enabled |
| `ALLOWED_ORIGINS` | Yes | localhost ports | Comma-separated; no wildcard in prod |
| `DEEPSEEK_API_KEY` | Required for AI | empty | AI conversations disabled if not set |
| `CLOUDINARY_*` | Required for uploads | empty | Media upload returns 503 if not set |
| `TWILIO_*` | Optional | empty | SMS channel skipped if not set |
| `SENDGRID_API_KEY` | Optional | empty | Email channel skipped if not set |
| `FCM_SERVER_KEY` | Optional | empty | Push channel skipped if not set |
| `SENTRY_DSN` | Optional | empty | Error tracking disabled if not set |
| `ENABLE_METRICS` | Optional | `true` | Set `false` to disable /metrics |

### Scaling and database connection budget

The API image runs four Uvicorn workers. SQLAlchemy pools are per process, so
the upper bound is:

```text
api containers * 4 workers * (DATABASE_POOL_SIZE + DATABASE_MAX_OVERFLOW)
```

The production Compose defaults therefore allow at most 60 application
connections for one API container. Reserve database connections for migrations,
workers, monitoring, and administration. To add API containers, verify the
managed PostgreSQL connection limit first, then run:

```bash
docker compose -f docker-compose.prod.yml up -d --scale api=2
```

Do not rely on `deploy.replicas` with ordinary Docker Compose; that field is a
Swarm deployment control. High user counts require a production-sized dataset,
distributed load tests, connection-pool monitoring, and horizontal scaling;
they cannot be certified from a local smoke test.

---

## Migration Commands

```bash
# Apply all pending migrations (safe on existing DB)
alembic upgrade head

# Check current migration version
alembic current

# Show migration history
alembic history --verbose

# Rollback one migration (use carefully — may be destructive)
alembic downgrade -1
```

---

## Background Jobs

```bash
# Notification dispatch (run every 1 minute)
python -m app.jobs.notifications dispatch

# Notification retry (run every 5 minutes)
python -m app.jobs.notifications retry

# Notification cleanup (run hourly)
python -m app.jobs.notifications cleanup

# Draft/slot-hold expiry (run every 15 minutes)
python -m app.jobs.expire_drafts
```

See `scripts/cron_jobs.sh` for crontab format.

---

## Rollback Plan

### Backend Rollback
```bash
# Roll back to previous image tag
docker compose -f docker-compose.prod.yml \
  set IMAGE_TAG=<previous-tag>
docker compose -f docker-compose.prod.yml up -d api

# Roll back migration (only if no destructive DDL in the migration)
docker compose -f docker-compose.prod.yml run --rm api alembic downgrade -1
```

### Frontend Rollback
```bash
# Re-deploy previous Next.js build (rebuild with previous git tag)
git checkout <previous-tag>
cd frontend/super-admin && npm ci && npm run build
cd frontend/tenant-portal && npm ci && npm run build
# Re-deploy to hosting platform
```

### Database Backup & Restore
```bash
# Backup
pg_dump -h HOST -U USER -d serviceos -Fc -f serviceos_$(date +%Y%m%d_%H%M%S).dump

# Restore to a test database
pg_restore -h HOST -U USER -d serviceos_restore --clean serviceos_<timestamp>.dump
```

### Emergency: Disable AI Calls
```bash
# In .env.production: clear the key then restart
DEEPSEEK_API_KEY=
docker compose -f docker-compose.prod.yml up -d api
# All AI endpoints return 503 safely
```

### Emergency: Disable Notifications
```bash
# Stop the cron job / notification worker
# The API continues to work; notifications queue but don't dispatch
```

### Maintenance Mode
```bash
# Return 503 for all API traffic via nginx
# Edit nginx.conf: replace proxy_pass with:
#   return 503 '{"error": "Fuvay is in maintenance mode"}';
# Reload nginx:
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## Health & Readiness Endpoints

| Endpoint | Purpose | HTTP Status |
|---|---|---|
| `GET /health` | Load-balancer heartbeat | 200 ok / 503 down |
| `GET /v1/health` | Versioned alias — same response | 200 ok / 503 down |
| `GET /v1/ready` | Readiness gate — confirms DB + Redis live | 200 ready / 503 not-ready |
| `GET /docs` | Swagger UI | 200 |
| `GET /redoc` | ReDoc UI | 200 |
| `GET /openapi.json` | OpenAPI schema | 200 |
| `GET /metrics` | Prometheus metrics (internal only) | 200 |

---

## Mini Production Smoke Checklist

```
POST /v1/auth/login                     → 200 access_token
GET  /v1/auth/me                        → 200 user object
GET  /v1/admin/tenants?page=1&page_size=25  → 200 paginated list
GET  /v1/provider/service-jobs?page=1   → 200 paginated list
GET  /v1/customer/bookings?page=1       → 200 paginated list
GET  /health                            → status: ok
GET  /v1/ready                          → ready: true
GET  /docs                              → Swagger UI renders
```
