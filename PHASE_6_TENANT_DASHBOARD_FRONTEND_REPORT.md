# Phase 6 — Tenant Dashboard Frontend Report

## App

`frontend/tenant-portal/` — a separate, dedicated Next.js app (distinct
from `frontend/super-admin/`), port 3001. Confirmed via research: dozens of
pre-built route groups under `app/(tenant)/` covering dashboard, profile,
staff, service-areas, catalog, services, packages, wallet, documents,
onboarding-status, settings, users, notifications, plus a `provider/`
subtree (status, offerings, service-areas, team-members, availability,
wallet, compliance). Own login/register/forgot-password/change-password
flows exist.

TypeScript: **0 errors** (confirmed this sprint, no frontend code changed —
all 2 bugs found were backend-only).

## Forbidden label scan (frontend)

Two initial grep hits, both reviewed and confirmed **not violations**:
- `app/(tenant)/account/privacy/page.tsx`: a `WITHDRAWABLE` set refers to
  GDPR-style **consent withdrawal**, unrelated to financial withdrawal —
  false positive.
- `app/(tenant)/jobs/[id]/page.tsx` (2 occurrences): *"Provider usage
  credits are not real money and are not withdrawable."* — an explicit,
  correct compliance disclaimer (a negation, not a violation), matching the
  exact business rule this ticket requires.

Zero actual forbidden-label violations found.

## Result: **Frontend certified.** No code changes were needed on the tenant-portal frontend this sprint — the 2 real bugs found (dangling tenant_id, request_id placeholder) were both backend-only. TypeScript clean; forbidden-label scan clean (2 reviewed false positives, 0 real violations).
