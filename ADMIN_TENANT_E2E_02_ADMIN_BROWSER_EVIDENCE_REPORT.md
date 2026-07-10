# Browser Evidence Report (Part 15)

Evidence root: `frontend/e2e-admin-tenant/evidence/e2e02/` (26 files: 20 screenshots + 4 logs +
2 text files). User for all: `admin@serviceos.in` (super_admin), real Chrome via
`channel: 'chrome'`, session via real `/v1/auth/login`.

| Route | Sidebar active | Breadcrumb | Title/subtitle | API/data state | Screenshot | Notes |
|---|---|---|---|---|---|---|
| /admin/dashboard | dashboard | none (Part 4 gap) | present | data loaded | `smoke_admin_dashboard.png` | 200, len=4336 |
| /admin/tenants | tenants | none | present | data loaded | `smoke_admin_tenants.png` | 200, len=2546 |
| /admin/bookings | bookings | none | present | data loaded | `smoke_admin_bookings.png` | 200, len=1207 |
| /admin/customers | customers | none | present | data loaded | `smoke_admin_customers.png` | 200, len=1162 |
| /admin/categories | categories | none | present | data loaded | `smoke_admin_categories.png` | 200, len=1472 |
| /admin/pricing-tiers | pricing-tiers | none | present | data loaded | `smoke_admin_pricing-tiers.png` | 200, len=1637 |
| /admin/home-services/service-catalog | hs-service-catalog | none | present | data loaded | `smoke_admin_home-services_service-catalog.png` | 200, len=2517 |
| /admin/finance | finance | none | present | data loaded | `smoke_admin_finance.png` | 200, len=1703 |
| /admin/marketing | marketing | none | present | data loaded | `smoke_admin_marketing.png` | 200, len=2294, slower settle (~15s) |
| /admin/engines | engines | none | present | data loaded | `smoke_admin_engines.png` | 200, len=3723 |
| /admin/security | security | none | present | data loaded | `smoke_admin_security.png` | 200, len=1440, slower settle (~10s) |
| /admin/audit-logs | audit-logs | none | present | data loaded | `smoke_admin_audit-logs.png` | 200, len=2842, uses direct fetch() (Part 12) |
| /admin/users | users | none | present | data loaded | `smoke_admin_users.png` | 200, len=1923, slower settle (~9s) |
| /admin/home-services/pricing-rules | hs-pricing-rules (600 weight, confirmed) | none | present | data loaded | `_admin_home-services_pricing-rules.png` | active-state fix verified |
| /admin/home-services/service-catalog (active-state case) | hs-service-catalog (600 weight) | none | present | data loaded | `_admin_home-services_service-catalog.png` | active-state fix verified |
| /admin/tenants/onboarding | onboarding (600 weight) | none | present | data loaded | `_admin_tenants_onboarding.png` | active-state fix verified |
| /admin/onboarding/providers | onboarding-providers (600 weight) | none | present | data loaded | `_admin_onboarding_providers.png` | active-state fix verified |
| /admin/users/roles | roles (600 weight) | none | present | data loaded | `_admin_users_roles.png` | active-state fix verified — was broken pre-fix |
| /admin/users/permissions | permissions (600 weight) | none | present | data loaded | `_admin_users_permissions.png` | active-state fix verified — was broken pre-fix |
| dashboard post-login | dashboard | none | present | data loaded | `shell-dashboard.png` | sidebar+header confirmed present |
| corrupted token → /admin/dashboard | n/a (redirected) | n/a | n/a | redirected to /login | `corrupted-token.png` | no explicit "session expired" copy (Part 9 gap) |
| /admin/tenants @1024px | tenants | none | present | data loaded | `responsive-1024.png` | no overflow |
| /admin/tenants @1280px | tenants | none | present | data loaded | `responsive-1280.png` | no overflow |
| /admin/tenants @1440px | tenants | none | present | data loaded | `responsive-1440.png` | no overflow |

No request_id-bearing error state was encountered during this pass (no route returned an error) —
`ApiErrorState`/`RequestIdBadge` render paths were verified by code read (Part 8) but not
triggered live in this pass; triggering a live 500/403 was outside scope of shell/nav smoke.
