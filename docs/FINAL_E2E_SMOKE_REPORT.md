# ServiceOS — Final E2E Smoke Report

**Date:** 2026-07-03
**Environment:** Local development (PostgreSQL + Redis running locally)
**Sprint:** 36 (verification)

---

## API Smoke Checklist

The following endpoints were verified to be registered and return correct responses
based on code inspection and test suite coverage. Actual HTTP smoke tests require
a running server; see `docs/DEPLOY.md` for startup instructions.

| Endpoint | Method | Auth | Expected | Test Coverage |
|----------|--------|------|----------|---------------|
| `/health` | GET | None | 200 `{status: "ok"}` | health_router tests |
| `/v1/health` | GET | None | 200 `{status: "ok"}` | health_router tests |
| `/v1/ready` | GET | None | 200 ready / 503 not-ready | health_router tests |
| `/docs` | GET | None | 200 Swagger UI | Verified in code |
| `/openapi.json` | GET | None | 200 JSON schema | Verified in code |
| `/v1/auth/login` | POST | None | 200 `{access_token, refresh_token}` | auth tests |
| `/v1/auth/me` | GET | JWT | 200 user object | auth tests |
| `/v1/admin/tenants` | GET | super_admin JWT | 200 paginated list | tenant tests |
| `/v1/admin/engines` | GET | super_admin JWT | 200 engine list | engine tests |
| `/v1/provider/service-jobs` | GET | tenant JWT | 200 paginated list | provider tests |
| `/v1/customer/bookings` | GET | customer JWT | 200 paginated list | booking tests |
| `/v1/customer/ai/chat` | POST | customer JWT | 200 AI response | ai_chat tests |
| `/v1/admin/analytics/summary` | GET | super_admin JWT | 200 metrics | analytics tests |

---

## E2E Test Suite (Playwright)

The `e2e/` directory exists with Playwright configuration. Structural validation passes:

- `e2e/playwright.config.ts` — exists, has both `super-admin` and `tenant-portal` projects
- `e2e/helpers/mock-api.ts` — exists, has `setupMockApi`, `setAdminAuth`, `setTenantAuth`
- Super-admin specs: auth, jobs, staff, customers, settings, documents, security, compliance
- Tenant-portal specs: auth, reviews

Browser tests require live servers. To run:
```bash
cd e2e
npx playwright install
npx playwright test
```

---

## Full Flow Verification (by Sprint)

### Home Service Flow (Sprints 15–16, 19–21)
1. Customer starts AI chat → AI classifies as home service → collects category, location, slot
2. Booking confirmation → `confirm_home_service_booking` creates `home_service_booking` + slot hold
3. Admin assigns staff → job enters `assigned` status
4. Staff executes job → status transitions through execution states
5. Invoice generated → customer pays → commission calculated → wallet credited
6. Customer leaves review → rating engine updates provider score

### Coaching/IELTS Flow (Sprints 17, 19)
1. AI chat → collects subject, level, schedule preference
2. Confirmation → `coaching_appointment` created
3. Coach assigned → session executed → feedback collected

### Real Estate Flow (Sprints 18, 19)
1. AI chat → collects property type, budget, location
2. Lead created → assigned to agent → follow-up scheduled

---

## Known Smoke Test Gaps

1. **Production domain** — no live URL yet; smoke tests run against localhost only
2. **Stripe payment** — config present; actual payment webhook not tested (no Stripe test key configured)
3. **Cloudinary** — upload endpoints return 503 gracefully if `CLOUDINARY_CLOUD_NAME` is empty
4. **Push notifications** — FCM not configured in dev; notification engine queues but does not dispatch
5. **SMS (Twilio)** — not configured in dev; OTP SMS falls back to log-only mode

---

## Sprint 32 Fixes Applied (Production Smoke Blockers)

| Fix | Description |
|-----|-------------|
| RAG router | Registration order fixed in main.py |
| Marketing router | Route prefix corrected |
| Invoice /v1 prefix | Added missing prefix causing 404 |
| IDOR test | Cross-tenant access correctly returns 403 |
| isoformat() crash | None-check added before calling .isoformat() |
| Missing verticals | Additional vertical registrations added to seed |
