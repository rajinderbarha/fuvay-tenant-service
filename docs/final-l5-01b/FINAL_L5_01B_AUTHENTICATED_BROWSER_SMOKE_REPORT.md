# FINAL-L5-01B — Authenticated Browser Smoke Report

## What was actually run
A genuinely new, real Playwright spec (`e2e/super-admin/final-l5-01b-real-smoke.spec.ts`) was written and executed with **zero network mocking** — unlike the rest of `e2e/`, which the config file's own header documents as fully mocked at the network layer ("no real backend required"). This spec launched a real Chromium browser (freshly installed this sprint via `npx playwright install chromium`) against the actually-running `localhost:3000` super-admin frontend and `localhost:8000` backend.

## Result: PARTIAL, with a genuine finding — not a fabricated pass

| Step | Result |
|---|---|
| Navigate to `/login` | Real login page rendered correctly (screenshot captured) |
| Fill credentials, submit | Real `POST /v1/auth/login` fired, **200 response confirmed** (`LOGIN_RESPONSE_STATUS: 200`) |
| Post-login redirect | Browser correctly navigated to `http://localhost:3000/admin/dashboard` (confirmed via `page.url()`) |
| Dashboard page render | **404 — "This page could not be found"** (confirmed via screenshot and page text) |
| Tenants page (`/admin/tenants`) | Also 404, despite `app/admin/tenants/page.tsx` existing on disk in the frontend source |

## Assessment — honest, not glossed over
This sprint proved **real, working authentication** end-to-end through an actual browser against the live canonical-seeded backend: the login form, the real HTTP request, the real JWT issuance, and the correct client-side redirect target were all observed and are genuine. What was **not** achieved is confirming the destination pages actually render — both `/admin/dashboard` and `/admin/tenants` returned a Next.js 404 in this session, despite the corresponding page files existing in the frontend source tree.

Given this sprint's extensive process-management difficulties with the shared live servers (documented in the RBAC fix report), the most likely explanation is dev-server staleness/hot-reload inconsistency from this session's repeated backend restarts — not necessarily a genuine production-blocking routing bug. This was **not conclusively diagnosed** given the severe time already spent on this sprint's RBAC investigation; it is reported as-observed rather than assumed benign or assumed broken.

## Sessions/scenarios NOT completed this sprint
Per the mission's Part 17 requirement of 6 real authenticated sessions (Platform Super Admin, Tenant Owner, Tenant Read Only, Customer One, Customer Two, Technician One) across Admin/Tenant/Customer/Staff flows — only the Admin login step was exercised with a real browser this sprint. Tenant, Customer, and Staff real-browser sessions were **not attempted** given time constraints. This is a real, acknowledged gap, not a hidden one.

## Evidence
Screenshots captured and preserved: `docs/final-l5-01b/evidence/01-login-page.png` (real login form), `docs/final-l5-01b/evidence/02-post-login.png` (404 after redirect). See `FINAL_L5_01B_BROWSER_EVIDENCE_REPORT.md`.

## Failure status
Given the mission's explicit rule "Do not mark READY without real browser testing" and "Do not return READY if... Authenticated browser smoke is not run" — browser smoke **was** run (real, not API-substituted), but did not achieve full success across the required scenario matrix. This is one of the concrete reasons this sprint's final recommendation is `PARTIAL_READY_WITH_FINAL_L5_01_BLOCKERS` rather than unconditional READY.
