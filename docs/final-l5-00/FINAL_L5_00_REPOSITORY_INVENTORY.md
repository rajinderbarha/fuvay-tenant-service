# FINAL-L5-00 — Repository Inventory (Parts 3-4)

Generated: 2026-07-10. Read-only survey of `g:\serviceos`. No source files were modified.

## 1. Top-level layout

| Path | Purpose | Language/Framework | Entry point | Build/Test | Notes |
|---|---|---|---|---|---|
| `app/` | Backend API (FastAPI monolith) | Python 3.12, FastAPI, SQLAlchemy async | `app/main.py` (`app.title="ServiceOS API"`) | `uvicorn app.main:app --reload` / `pytest` | 75 `app.include_router(...)` calls in `main.py`; 143 files matching `*router*.py`; 69 subpackages under `app/engines/` (one per domain: booking, dispatch, complaints, brands, ai_chat, ...); `app/core/` has 13 cross-cutting modules (tenant_scope, staff_scope, permissions, pagination, idempotency, pii_filter, etc.) |
| `frontend/super-admin/` | Admin web app | Next.js (App Router), TypeScript, Tailwind, Recharts | `app/` dir, `npm run dev` (port 3000) | `next build` / `next lint` (no dedicated `tsc` script; type-check via `next build` or ad hoc `tsc --noEmit`) | Has `.next/`, `node_modules/`, `tests/`, `docs/e2e06c`, `docs/e2e12` subfolders (own report archives) |
| `frontend/tenant-portal/` | Tenant/provider portal web app | Next.js, TypeScript | `app/`, `npm run dev` (port 3001) | `next build` / `next lint` | Mirrors super-admin structure |
| `frontend/customer-app/` | Customer-facing web app | Next.js, TypeScript | `app/`, `npm run dev` (port 3002) | `next build` / `next lint` | |
| `frontend/e2e-admin-tenant/` | Cross-app Playwright E2E harness | TypeScript, Playwright | `playwright.config.ts` | `npm test` (playwright test) | Not a runnable app; drives super-admin + tenant-portal together; has `helpers/`, `super-admin/`, `tenant-portal/` spec dirs |
| `mobile/customer-app/` | Customer mobile app | React Native (Expo), TypeScript | `expo start` | `npm run android` / `ios` / `lint` | |
| `mobile/staff-app/` | Field staff mobile app | React Native (Expo), TypeScript | `expo start` | same as above | |
| `design-system/` | Shared UI/token library used by web frontends | TypeScript | `index.ts` | (no standalone `package.json` found at `design-system/` root — consumed directly via relative import/workspace path, not published as its own npm package) | Subfolders: `components/`, `hooks/`, `styles/`, `tokens/`, `tests/`, `showcase/` |
| `alembic/` | DB migrations | Python (Alembic) | `alembic.ini` (repo root) + `alembic/env.py` | `alembic upgrade head` | 125 migration files in `alembic/versions/`, ranging from `001_initial_schema.py` to `131_admin_e2e06_report_runs_updated_at.py` (non-contiguous — some sprint numbers skipped/merged) |
| `tests/` | Backend unit/integration tests (pytest) | Python | `tests/conftest.py` | `pytest` (config in `pyproject.toml`: `testpaths=["tests"]`, `asyncio_mode=auto`) | 199 `test_*.py` files; has `tests/archive/` for retired suites |
| `e2e/` | Root-level Playwright E2E (separate from `frontend/e2e-admin-tenant`) | TypeScript, Playwright | `playwright.config.ts` | `npm test`/`npx playwright test` | Subdirs `super-admin/`, `tenant-portal/`, `helpers/` — appears to be an earlier/parallel E2E harness alongside `frontend/e2e-admin-tenant/` |
| `scripts/` | Ops/seed scripts | Python | various `scripts/*.py` | run individually, e.g. `python scripts/seed_x.py` | 22 scripts total, 15 are `seed_*.py` (master data / demo data seeding) |
| `docs/` | Structured project documentation (distinct from root loose reports) | Markdown | — | — | Contains `DEPLOY.md`, `FINAL_*` reports (API coverage, deployment, E2E smoke, executive summary, known issues, level-5 proof, performance, release decision, security proof, tenant isolation), plus `PHASE_6B_*` and `ADMIN_TENANT_DETAIL_*` report sets. This mission's outputs (`FINAL_L5_00_*`) now live in `docs/final-l5-00/` |
| Repo root loose `*.md` reports | Per-sprint/per-feature audit & certification artifacts generated during development | Markdown | — | — | **663 files** at repo root. Naming patterns by prefix/count: `ADMIN_*` (226, incl. `ADMIN_A2_*`, `ADMIN_A3_*`, `ADMIN_A11_*`, `ADMIN_TENANT_E2E_*` sub-series), `PHASE_*` (118), `CUSTOMER_*` (48), `TENANT_*` (42), `FRONTEND_*` (16), `HS0`–`HS10`/`HS*B` home-services sprint series (~15 sub-prefixes, ~140 files combined), `TYPE_*` (7), `AUTO_*` (6), `HOME_*` (5), `PROVIDER_*`/`JOB_*`/`CROSS_*` (3 each), plus a few `MANUAL_*`, `DATA_*`, `TEST_*`. These are point-in-time certification/test-result/blocker reports, not living documentation — not individually catalogued here per mission scope |
| `.github/workflows/` | CI/CD | YAML | — | — | 4 workflows: `build.yml`, `deploy.yml`, `e2e.yml`, `test.yml` |
| `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml` | Container build & local orchestration | Docker | `Dockerfile` → `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000` | `docker compose up` | Dev compose brings up `api` (8000), `postgres` (pgvector/pg17, 5432), `redis` (6379), optional `pgadmin` (5050) and `redis_commander` (8081) under `--profile dev` |
| `nginx.conf` | Reverse proxy config | Nginx | — | — | Root-level single config file (no `nginx/` directory) |
| `monitoring/` (`grafana/`, `prometheus.yml`) | Observability stack config | Grafana/Prometheus | — | — | |
| `.env.example`, `.env` | Backend environment templates | dotenv | — | — | `.env.example` is the checked-in template (5.3 KB); `.env` present locally (not for commit) |
| `frontend/*/.env.local`, `.env.local.example` | Per-frontend environment | dotenv | — | — | All three Next.js apps point `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| `pyproject.toml`, `requirements.txt`, `alembic.ini` | Python project/dependency/migration config | — | — | — | `pyproject.toml` currently only carries `[tool.pytest.ini_options]` and `[tool.ruff]` (no `[project]`/build-system table — not a packaged Python project, just tooling config) |
| `.vscode/`, `.pytest_cache/`, `.claude/` | Editor/tooling artifacts | — | — | — | Not part of application code |

## 2. Backend module survey (`app/`)

- **Entry point:** `app/main.py` (680 lines), FastAPI app titled `"ServiceOS API"`, registers 75 routers.
- **`app/engines/`**: 69 subdirectories, one per business domain/vertical (e.g. `booking`, `dispatch`, `complaints`, `brands`, `chat`, `coaching_appointment`, `customer_credits`, `customer_flow`, `customer_reviews`, `dashboard_command_center`, `data_science`, `admin_catalog`, `ai_chat`, `ai_conversation`, `analytics`, `appointment`, `auth`, `compliance`, and more). This is the dominant architectural pattern — feature-sliced "engines" rather than a single flat `models/`+`routers/` split.
- **`app/models/`**: only 2 top-level files (`base.py` + `__init__.py`); actual ORM models are distributed inside each engine package (60 files repo-wide match `*model*.py`) rather than centralized.
- **`app/core/`**: 13 cross-cutting modules — `audit.py`, `customer_scope.py`, `events.py`, `feature_flags.py`, `hateoas.py`, `idempotency.py`, `logging.py`, `pagination.py`, `permissions.py`, `pii_filter.py`, `security.py`, `staff_scope.py`, `tenant_scope.py`, `usage_quota.py`.
- Other top-level `app/` packages: `dependencies/`, `integrations/`, `jobs/`, `schemas/`, `middleware.py`, `exceptions.py`, `observability.py`, `redis_client.py`, `cloudinary_client.py`, `email_client.py`, `twilio_client.py`, `config.py`, `database.py`, `engine_registry/`.

## 3. Migrations

- Directory: `alembic/versions/`
- Count: **125 files**
- Range: `001_initial_schema.py` → `131_admin_e2e06_report_runs_updated_at.py` (numbering has gaps — not every integer 1–131 is present, consistent with squashed/renumbered sprints referenced in project memory, e.g. migrations 020, 026–089 etc. mentioned across sprint logs).

## 4. Seeds

- `scripts/` has 22 files total, **15** are `seed_*.py` (master data, demo/brand/category/starter-pack seeding referenced throughout sprint history).

## 5. Tests

- Backend: `tests/` — 199 `test_*.py` files, pytest config in `pyproject.toml` (`asyncio_mode=auto`), retired suites moved to `tests/archive/`.
- Frontend/E2E: two parallel Playwright harnesses — root `e2e/` (super-admin + tenant-portal specs, own `playwright.config.ts`) and `frontend/e2e-admin-tenant/` (`serviceos-admin-tenant-e2e` package, same two-app scope). Each frontend app additionally has its own `tests/` folder (e.g. `frontend/super-admin/tests/`).

## 6. Generated reports (root loose `*.md`)

663 files at repo root, not part of application runtime. See table row above for prefix breakdown. These represent iterative certification/audit output from prior sprints (API mapping reports, data accuracy reports, permission reports, forbidden-label scans, test results, remaining-blockers trackers) and should be considered disposable historical artifacts, not source of truth — current status should be read from `docs/` FINAL_* reports and project memory, not these root files.

## 7. Deployment & CI

- **Docker:** `Dockerfile` (builds API image, `uvicorn` CMD on port 8000), `docker-compose.yml` (dev: api+postgres+redis+optional pgadmin/redis-commander), `docker-compose.prod.yml` (production variant).
- **Reverse proxy:** `nginx.conf` at repo root.
- **Monitoring:** `monitoring/prometheus.yml`, `monitoring/grafana/`.
- **CI/CD:** `.github/workflows/build.yml`, `deploy.yml`, `e2e.yml`, `test.yml`.

## 8. Environment examples

- `.env.example` (backend, repo root)
- `frontend/super-admin/.env.local.example`, `frontend/tenant-portal/.env.local.example` (customer-app has `.env.local` present but no example file found)
- All frontend env files set `NEXT_PUBLIC_API_URL=http://localhost:8000` and `NEXT_PUBLIC_USE_MOCK=false`.

## 9. Static assets / design system

- `design-system/` is a shared TS library (components, hooks, tokens, styles) consumed by the three Next.js apps; it has no independent `package.json`, so it is imported by relative/workspace path rather than as a versioned npm package.
