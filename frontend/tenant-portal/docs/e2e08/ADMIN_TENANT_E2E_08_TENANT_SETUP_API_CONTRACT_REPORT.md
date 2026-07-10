# ADMIN-TENANT-E2E-08: Tenant Setup API Contract Report

**Date:** 2026-07-10

## API Contracts (Setup Pages)

### Onboarding / Checklist
| Method | Path | Used by |
|--------|------|---------|
| GET | `/v1/provider/onboarding/status` | onboarding-status/page.tsx |
| GET | `/v1/provider/onboarding/items` | onboarding-status/page.tsx |
| POST | `/v1/provider/onboarding/refresh` | onboarding-status/page.tsx |
| GET | `/v1/provider/package/summary` | onboarding-status/page.tsx |

### Business Profile
| Method | Path | Used by |
|--------|------|---------|
| GET | `/v1/provider/business-profile` | profile/page.tsx |
| PUT | `/v1/provider/business-profile` | profile/page.tsx |
| POST | `/v1/provider/business-profile/submit-review` | profile/page.tsx |
| GET | `/v1/me` | profile/page.tsx (profileApi.getProfile) |
| PUT | `/v1/me` | profile/page.tsx (profileApi.updateProfile) |
| POST | `/v1/media/business-logo` | profile/page.tsx |
| POST | `/v1/media/shop-photo` | profile/page.tsx |

### Service Areas
| Method | Path | Used by |
|--------|------|---------|
| GET | `/v1/provider/service-areas` | provider/service-areas/page.tsx |
| GET | `/v1/provider/service-areas/limits` | provider/service-areas/page.tsx |
| POST | `/v1/provider/service-areas` | provider/service-areas/page.tsx |
| PUT | `/v1/provider/service-areas/{id}` | provider/service-areas/page.tsx |
| DELETE | `/v1/provider/service-areas/{id}` | provider/service-areas/page.tsx |
| POST | `/v1/provider/service-areas/{id}/set-primary` | provider/service-areas/page.tsx |
| POST | `/v1/provider/service-areas/validate` | provider/service-areas/page.tsx |

### Availability
| Method | Path | Used by |
|--------|------|---------|
| GET | `/v1/provider/availability` | tenant/setup/availability/page.tsx |
| POST | `/v1/provider/availability` | tenant/setup/availability/page.tsx |
| PUT | `/v1/provider/availability/{id}` | tenant/setup/availability/page.tsx |
| DELETE | `/v1/provider/availability/{id}` | tenant/setup/availability/page.tsx |
| POST | `/v1/provider/availability/preset/{id}` | tenant/setup/availability/page.tsx |
| DELETE | `/v1/provider/availability/preset/{id}` | tenant/setup/availability/page.tsx |

### Shared / Supporting
| Method | Path | Used by |
|--------|------|---------|
| GET | `/v1/provider/status` | multiple pages |
| GET | `/v1/provider/team-members` | availability page (scope options) |
| GET | `/v1/tenant/setup/activity` | service-areas + availability pages |
| GET | `/v1/auth/me` | profile page (permissions) |

## Transport
All calls use `apiFetch` from `lib/api.ts` — Authorization header, JSON body, typed error handling via `ServiceOSError`.
