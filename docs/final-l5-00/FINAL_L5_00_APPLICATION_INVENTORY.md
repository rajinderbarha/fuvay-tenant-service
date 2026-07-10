# FINAL-L5-00 — Application Inventory (Parts 3-4)

Generated: 2026-07-10. Read-only survey of `g:\serviceos`. For each runnable application: framework, port, commands, env, DB dependency, and inferred startup status.

---

## 1. Backend API

- **Path:** `app/` (repo root Python package)
- **Framework:** FastAPI + SQLAlchemy (async) + Alembic, Python 3.12
- **Port:** 8000 (per `docker-compose.yml` and `Dockerfile` CMD)
- **Entry command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (dev, per `docker-compose.yml`); `Dockerfile` CMD identical without `--reload`
- **Build command:** N/A (interpreted; container build via `docker build .`)
- **Type-check command:** N/A (Python; no mypy config found at root — `pyproject.toml` only configures `pytest` and `ruff`)
- **Test command:** `pytest` (config in `pyproject.toml`: `testpaths=["tests"]`, `asyncio_mode="auto"`)
- **Env file:** `.env` (local, gitignored), template `.env.example`
- **API base URL config:** self — this is the API; consumed by frontends via `NEXT_PUBLIC_API_URL`
- **DB dependency:** PostgreSQL (`pgvector/pgvector:pg17` image in compose, for RAG/embedding support) + Redis (session/cache, `redis:7.2-alpine`)
- **Startup status:** Per project memory (`Sprint 35 complete`, `Sprint 36 complete`), status was `READY_FOR_DEPLOYMENT` then `STAGING_READY` as of those sprints. Most recent root reports (`ADMIN_TENANT_E2E_09B_*`, dated most recently among root `*.md` files) are E2E test/blocker reports for admin+tenant flows rather than a fresh top-level readiness verdict — treat backend as last-known STAGING_READY pending re-verification; source: `docs/FINAL_RELEASE_DECISION.md`, `docs/FINAL_LEVEL_5_PROOF_REPORT.md` in `docs/`.

---

## 2. Super Admin (frontend)

- **Path:** `frontend/super-admin/`
- **Framework:** Next.js (App Router), TypeScript, Tailwind, Recharts (`package.json` name: `serviceos-super-admin`)
- **Port:** 3000 (`"dev": "next dev --port 3000"`)
- **Entry command:** `npm run dev`
- **Build command:** `npm run build` (`next build`)
- **Type-check command:** no dedicated `tsc` script in `package.json`; type errors surface via `next build`. `tsconfig.json` present at `frontend/super-admin/tsconfig.json`.
- **Test command:** `npm run lint` only in package scripts; Jest/RTL or other unit test runner not found in scripts (has a `tests/` folder likely used by Playwright harnesses instead)
- **Env file:** `.env.local` (present), `.env.local.example` (present)
- **API base URL config:** `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local`; `NEXT_PUBLIC_USE_MOCK=false`
- **DB dependency:** none directly — talks to backend API only
- **Startup status:** Repo has a built `.next/` directory present (evidence of at least one successful local build/dev run). Numerous root `ADMIN_*` reports (e.g. `ADMIN_A11_FULL_E2E_CERTIFICATION_REPORT.md`, `ADMIN_A3_FINAL_CERTIFICATION_REPORT.md`) document per-module certification passes; most recent admin+tenant joint E2E series is `ADMIN_TENANT_E2E_09B_*` — cite these root files for the latest module-level status rather than a single global verdict.

---

## 3. Tenant Portal (frontend)

- **Path:** `frontend/tenant-portal/`
- **Framework:** Next.js, TypeScript (`package.json` name: `serviceos-tenant-portal`)
- **Port:** 3001 (`"dev": "next dev --port 3001"`)
- **Entry command:** `npm run dev`
- **Build command:** `npm run build`
- **Type-check command:** none dedicated (via `next build`)
- **Test command:** `npm run lint` only
- **Env file:** `.env.local`, `.env.local.example`
- **API base URL config:** `NEXT_PUBLIC_API_URL=http://localhost:8000`
- **DB dependency:** none directly — backend API only
- **Startup status:** per `TENANT_*` root reports and joint `ADMIN_TENANT_E2E_*` series; latest joint harness pass referenced is `ADMIN_TENANT_E2E_09B_*` (test results / blockers / browser evidence files at repo root).

---

## 4. Customer App (frontend)

- **Path:** `frontend/customer-app/`
- **Framework:** Next.js, TypeScript (`package.json` name: `serviceos-customer-app`)
- **Port:** 3002 (`"dev": "next dev --port 3002"`)
- **Entry command:** `npm run dev`
- **Build command:** `npm run build`
- **Type-check command:** none dedicated
- **Test command:** `npm run lint` only
- **Env file:** `.env.local` present at `frontend/customer-app/.env.local`; no `.env.local.example` found for this app (unlike super-admin/tenant-portal)
- **API base URL config:** not confirmed with a value in this survey pass (file present but content not matched in the `localhost:8000` grep for customer-app's `.env.local` — verify manually); `next.config.js` in this app does reference `localhost:8000`
- **DB dependency:** none directly — backend API only
- **Startup status:** `CUSTOMER_*` root reports (48 files) document feature-level pass/fail; no single global "READY" file found for this app specifically in this pass — treat as partially verified per those per-feature reports.

---

## 5. mobile/customer-app

- **Path:** `mobile/customer-app/`
- **Framework:** React Native via Expo, TypeScript (`package.json` name: `serviceos-customer-app` — **note: name collision with `frontend/customer-app`**, both named `serviceos-customer-app`)
- **Port:** N/A (Expo dev server, default 19000/8081 range, not explicitly configured in `package.json`)
- **Entry command:** `npm start` (`expo start`); `npm run android` / `npm run ios` for device/simulator builds
- **Build command:** handled by Expo/EAS tooling, not present as an npm script
- **Type-check command:** not present as a script (would need manual `tsc --noEmit` if `tsconfig.json` exists)
- **Test command:** `npm run lint` only (`eslint src --ext .ts,.tsx`)
- **Env file:** not confirmed in this pass — recommend checking `mobile/customer-app/.env*` directly
- **API base URL config:** not confirmed in this pass
- **DB dependency:** none directly — backend API only
- **Startup status:** Per project memory, `Sprint 15` notes "mobile AIChatScreen updated" — mobile apps receive incremental updates alongside backend sprints but no dedicated mobile readiness report was found among root `*.md` files in this survey pass.

---

## 6. mobile/staff-app

- **Path:** `mobile/staff-app/`
- **Framework:** React Native via Expo, TypeScript (`package.json` name: `serviceos-staff-app`)
- **Port:** N/A (Expo dev server)
- **Entry command:** `npm start` (`expo start`)
- **Build command:** Expo/EAS tooling (no npm script)
- **Type-check command:** not present as a script
- **Test command:** `npm run lint` only
- **Env file:** not confirmed in this pass
- **API base URL config:** not confirmed in this pass
- **DB dependency:** none directly — backend API only
- **Startup status:** no dedicated readiness report found among root `*.md` files.

---

## 7. e2e-admin-tenant harness

- **Path:** `frontend/e2e-admin-tenant/`
- **Framework:** Playwright, TypeScript (`package.json` name: `serviceos-admin-tenant-e2e`)
- **Port:** N/A (drives super-admin at :3000 and tenant-portal at :3001 as a client)
- **Entry command:** N/A (not a server)
- **Build command:** N/A
- **Type-check command:** `tsconfig.json` present; no dedicated script — TS compiled implicitly by Playwright's ts-node/esbuild pipeline
- **Test command:** `npm test` (`playwright test`), config in `playwright.config.ts`
- **Env file:** relies on target apps' running instances (likely `.env`/base URLs configured inside `playwright.config.ts` or spec helpers — not individually enumerated in this pass)
- **API base URL config:** indirect — through the two frontend apps under test, which point at `http://localhost:8000`
- **DB dependency:** indirect, via backend used by the apps under test
- **Startup status:** This harness produced the large `ADMIN_TENANT_E2E_*` series of root reports (login browser reports, route smoke reports, forbidden-label scans, remaining-blockers trackers). Most recent sub-series observed: `ADMIN_TENANT_E2E_09B_*` (test results, Playwright report, browser evidence, remaining blockers) — indicates active, iterative E2E certification rather than a single final pass; consult those specific files for the latest pass/fail detail per admin/tenant module.
- **Note:** A second, structurally similar harness exists at root `e2e/` (also Playwright, also covering `super-admin/` and `tenant-portal/`) — possible duplication; not resolved in this read-only survey.

---

## 8. design-system (shared package)

- **Path:** `design-system/`
- **Framework:** TypeScript component/token/hook library (no framework runtime of its own)
- **Port:** N/A
- **Entry command:** N/A — not run standalone; imported by the three Next.js apps
- **Build command:** none found (no `package.json` at `design-system/` root in this survey — consumed via direct relative/workspace import, not a compiled/published package)
- **Type-check command:** N/A at package level (type-checked as part of each consuming app's `next build`)
- **Test command:** has its own `tests/` and `showcase/` folders; exact test runner/script not confirmed in this pass (no root `package.json` found to inspect scripts — recommend checking for a nested config or verifying it's tested only via consuming apps)
- **Env file:** N/A
- **API base URL config:** N/A
- **DB dependency:** none
- **Startup status:** Referenced across many sprint completions (`Sprint 34B`, `Sprint 34A`) as the basis for the "White Gradient Design System" (globals.css v3, design-tokens.ts) — structurally stable per memory, not independently versioned/runnable.

---

## Cross-cutting notes

- **Port map:** Backend API 8000, Super Admin 3000, Tenant Portal 3001, Customer App 3002, pgAdmin 5050 (dev profile), Redis Commander 8081 (dev profile), Postgres 5432, Redis 6379.
- **Duplicate app name:** `frontend/customer-app/package.json` and `mobile/customer-app/package.json` both declare `"name": "serviceos-customer-app"` — cosmetic collision, not a build conflict since they're separate workspaces, but worth flagging for cleanup.
- **Status reporting caveat:** Root-level `*.md` "READY"/certification files are point-in-time and numerous (663 total); this report cites the most recent sub-series found per app (`ADMIN_TENANT_E2E_09B_*`) but does not assert current pass/fail — a fresh verification run is recommended before relying on any cited status.
