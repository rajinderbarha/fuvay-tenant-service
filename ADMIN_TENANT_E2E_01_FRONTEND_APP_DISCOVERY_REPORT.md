# ADMIN_TENANT_E2E_01 — Frontend App Discovery Report

## Admin app
- Path: `frontend/super-admin/`
- Framework: Next.js 16.2.9 + React 19.2.0 + TypeScript 5.8.3
- Dev command: `npm run dev` (`next dev --port 3000`)
- Build command: `npm run build` (`next build`)
- Lint command: `npm run lint` (`next lint`)
- Test command: none in package.json (no `test` script) — E2E now supplied externally via
  `frontend/e2e-admin-tenant`
- Base URL: http://localhost:3000
- Login route: `/login` (confirmed, real page at `app/login/page.tsx`)
- Env vars (`.env.local`):
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`
  - `NEXT_PUBLIC_USE_MOCK=false`

## Tenant app
- Path: `frontend/tenant-portal/`
- Framework: Next.js 16.2.9 + React 19.2.0 + TypeScript 5.8.3
- Dev command: `npm run dev` (`next dev --port 3001`)
- Build command: `npm run build` (`next build`)
- Lint command: `npm run lint` (`next lint`)
- Test command: none in package.json — E2E supplied externally
- Base URL: http://localhost:3001
- Login route: `/login` (confirmed, real page at `app/login/page.tsx`)
- Env vars (`.env.local`):
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`
  - `NEXT_PUBLIC_USE_MOCK=false`

Both apps route all live API calls through `lib/api.ts`, gated by `MOCK_MODE = NEXT_PUBLIC_USE_MOCK === "true"`,
which is `false` in both `.env.local` files — confirming no mocked responses are used in this environment.

## Real route inventories confirmed against filesystem
Admin (`frontend/super-admin/app/admin/`): dashboard, tenants, users, customers, staff, bookings,
operations, real-estate, coaching, bookability, onboarding, home-services/* (booking-drafts,
service-catalog, pricing-rules, price-experience, provider-matching, matching-diagnostics,
service-areas, completed-job-deduction, settings), catalog, service-groups, master-services,
issue-types, service-options, brands, brand-requests, types-brands, pricing, pricing-rules,
pricing-tiers, finance/* (claims, customer-credits, deposits, dispute-settlements, payouts,
tenant-penalties, topups, usage-credits, wallets), complaints, complaint-policies, review-*,
rework-requests, refund-requests, commission-records, financial-events, service-invoices,
notifications, notification-templates, notification-outbox, notification-events, chat, media,
compliance, security, audit-logs, engines, workflows, workflow-templates, checklists,
checklist-templates, verticals, location-mapping, marketing, analytics, reports, intelligence,
automation, service-setup, settings, account, profile.

Tenant (`frontend/tenant-portal/lib/nav-config.ts` + `app/(tenant)/`): /dashboard, /provider/status,
/profile, /provider/service-areas, /tenant/setup/services, /provider/service-coverage,
/provider/availability, /provider/staff, /finance/package, /finance/usage-credit-ledger,
/finance/security-deposit, /documents, /notifications, /activity, /settings, /jobs, /bookings,
/appointments, /dispatch, /customers, /reviews, /marketing, /chat, /analytics, /reports, plus a
separate `/staff/*` area for technicians and a legacy `/wallet` page (flagged in Part 14).

## Result
DISCOVERY COMPLETE — both apps, real ports, real routes, real env config confirmed.
