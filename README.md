# Fuvay — Multi-Tenant Home Services SaaS

A full-stack SaaS platform for managing home service businesses (AC repair, plumbing, electrical, cleaning, etc.) across multiple tenants, cities, and verticals.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Fuvay Platform                     │
│                                                          │
│  ┌────────────────┐    ┌──────────────────────────────┐  │
│  │  Super Admin   │    │   Tenant Owner Portal        │  │
│  │  (Next.js)     │    │   (Next.js)                  │  │
│  └───────┬────────┘    └──────────────┬───────────────┘  │
│          │                            │                   │
│  ┌───────▼────────────────────────────▼───────────────┐  │
│  │               FastAPI Backend                       │  │
│  │         26 Engines · REST API · WebSocket           │  │
│  └───────────────┬──────────────┬──────────────────────┘  │
│                  │              │                         │
│          ┌───────▼──────┐  ┌───▼────────┐               │
│          │  PostgreSQL  │  │   Redis    │               │
│          │  (pgvector)  │  │  (cache)   │               │
│          └──────────────┘  └────────────┘               │
│                                                          │
│  ┌───────────────┐   ┌────────────────────────────────┐  │
│  │  Staff App    │   │  Customer App                   │  │
│  │ (React Native)│   │  (React Native + DeepSeek AI)  │  │
│  └───────────────┘   └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Projects

| Project | Tech | Path | Port |
|---|---|---|---|
| **Backend API** | FastAPI + Python 3.13 | `app/` | 8000 |
| **Super Admin Portal** | Next.js 16 | `frontend/super-admin/` | 3000 |
| **Tenant Owner Portal** | Next.js 16 | `frontend/tenant-portal/` | 3001 |
| **Staff Mobile App** | Expo React Native | `mobile/staff-app/` | — |
| **Customer Mobile App** | Expo React Native | `mobile/customer-app/` | — |
| **Design System** | TypeScript | `design-system/` | — |
| **E2E Tests** | Playwright | `e2e/` | — |

## Quick Start

### Prerequisites
- Python 3.13, Node.js 20, Docker, Expo CLI

### 1. Backend
```bash
cp .env.example .env          # fill in values
docker compose up -d postgres redis
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 2. Super Admin Portal
```bash
cd frontend/super-admin
npm install && npm run dev     # → http://localhost:3000
```

### 3. Tenant Portal
```bash
cd frontend/tenant-portal
npm install && npm run dev     # → http://localhost:3001
```

### 4. Mobile Apps
```bash
cd mobile/staff-app            # or mobile/customer-app
npm install
npx expo start                 # scan QR with Expo Go
```

## Backend Engines (26)

| Category | Engines |
|---|---|
| **Core** | Auth, Tenant, Settings, Notification, Media, Webhook |
| **Commerce** | Platform Commerce, Billing Router, Pricing, Payment, Subscription |
| **Operations** | Dispatch, Field Ops, Booking, Appointment, Inventory |
| **Intelligence** | Data Science, RAG, Analytics, Marketing |
| **Compliance** | Security, Compliance, Document |
| **CRM** | Review, Chat, Geo |
| **AI** | AI Chat (DeepSeek) |

## Test Suite

```bash
# Run all tests (977 tests, 0 failures)
python -m pytest tests/ design-system/tests/ frontend/super-admin/tests/ \
  frontend/tenant-portal/tests/ mobile/staff-app/tests/ mobile/customer-app/tests/ -q
```

## CI/CD

- **Push** → runs all test suites (`.github/workflows/test.yml`)
- **Merge to main** → builds Docker image (`.github/workflows/build.yml`)
- **Release tag** → deploys to production (`.github/workflows/deploy.yml`)
- **PR to main** → runs Playwright E2E (`.github/workflows/e2e.yml`)

## Environment Variables

See `.env.example` for full list. Key variables:
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `SECRET_KEY` — 64-char random string for JWT signing
- `DEEPSEEK_API_KEY` — For AI chat engine
- `SENTRY_DSN` — Error tracking (optional)

## Monitoring

- **Health check**: `GET /health` — DB, Redis, engine status
- **Metrics**: `GET /metrics` — Prometheus metrics (set `ENABLE_METRICS=true`)
- **Production**: Prometheus + Grafana via `docker-compose.prod.yml`
