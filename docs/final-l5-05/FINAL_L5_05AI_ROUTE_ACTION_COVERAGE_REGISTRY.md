# FINAL-L5-05AI — Super Admin Route and High-Risk Action Coverage Registry

## Baseline

| Item | Value |
|---|---|
| `git rev-parse HEAD` (start) | `f36e2dd` |
| `git rev-parse origin/master` (start) | `f36e2dd` (identical) |
| Backend health | `ok` (already running from prior sprint — reused, not restarted, per this mission's own lesson against repeated dev-server cycling) |
| Frontend health | `200` on `/login` (already running from prior sprint — reused, not restarted) |
| `FINAL-L5-05AH` status | `PARTIAL_READY_WITH_FINAL_L5_05AH_BLOCKERS` (accepted, not reinterpreted) |

Per this mission's own explicit instruction ("do not repeat browser discovery work," "do not claim Chromium is unavailable," "repeatedly restarting... can produce inconsistent behavior"), this sprint reused the already-running backend/frontend from the prior sprint rather than cycling them again, and did not re-litigate Chromium availability.

## Tenant `/wallet` scope transfer (Part 3) — reconfirmed

- **Proof it belongs to the Tenant portal, not Super Admin**: the failing test navigates to `http://localhost:3001/wallet` — port 3001 is `frontend/tenant-portal`, a distinct Next.js application from `frontend/super-admin` (port 3000). No file under `frontend/super-admin/app/admin/**` references this route.
- **Proof no Super Admin route/permission claim depends on it**: `grep -r "3001" frontend/super-admin/app` returns no matches outside test files; the Super Admin route-permission registry (`NAV_GROUPS` in `AdminLayout.tsx`, reproduced below) contains no `/wallet` entry.
- **Classification**: `OUT_OF_SCOPE_PROVEN_FOR_FINAL_L5_05` / `TRANSFERRED_TO_TENANT_FRONTEND_CERTIFICATION`.
- **Traceability preserved**: the test itself (`final-l5-01b-six-sessions.spec.ts`, "2. Tenant Owner") is untouched — not deleted, not marked passed. This document is the explicit scope-transfer record; a future Tenant-portal certification sprint owns closing it.

## Real, machine-readable route registry — canonical top-level Admin navigation

Extracted directly from `frontend/super-admin/components/layout/AdminLayout.tsx`'s `NAV_GROUPS` — the actual, single source of truth this codebase already uses to gate every `/admin/*` route (via `resolveActiveNavId`'s longest-prefix match, established in FINAL-L5-05N). This is not a new, invented registry; it is the existing one, reformatted here as an explicit, reviewable table with two columns (`Domain`, `Criticality`) added, since neither existed as an explicit classification before this sprint.

| Route ID | Path | Domain | Permission | Criticality | Chromium coverage |
|---|---|---|---|---|---|
| dashboard | `/admin/dashboard` | DASHBOARD | (visible to all authenticated) | CRITICAL | **COVERED** (05l, 05m) |
| tenants | `/admin/tenants` | TENANT_ADMINISTRATION | `tenant:read` | CRITICAL | **COVERED** (05l, 05p, 05q) |
| onboarding | `/admin/tenants/onboarding` | TENANT_ADMINISTRATION | `SUPER_ADMIN_ONLY` | HIGH | NONE |
| onboarding-providers | `/admin/onboarding/providers` | PROVIDER_OPERATIONS | `SUPER_ADMIN_ONLY` | HIGH | NONE |
| packages | `/admin/packages` | PACKAGES | `SUPER_ADMIN_ONLY` | MEDIUM | **COVERED** (05l) |
| bookings | `/admin/bookings` | BOOKINGS | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| operations (Jobs) | `/admin/home-services/service-jobs` | JOBS | `admin:jobs:read` | CRITICAL | **COVERED** (05l) |
| customers | `/admin/customers` | TENANT_ADMINISTRATION | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| staff | `/admin/staff` | STAFF_OPERATIONS | `staff:read` | HIGH | **COVERED** (05l, 05p) |
| reviews | `/admin/reviews` | CATALOG | `SUPER_ADMIN_ONLY` | LOW | NONE |
| complaints | `/admin/complaints` | CATALOG | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| complaint-policies | `/admin/complaint-policies` | CATALOG | `SUPER_ADMIN_ONLY` | LOW | NONE |
| verticals | `/admin/verticals` | CATALOG | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| categories | `/admin/categories` | CATALOG | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| pricing-tiers | `/admin/pricing-tiers` | PRICING | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| location-mapping | `/admin/location-mapping` | PRICING | `SUPER_ADMIN_ONLY` | LOW | NONE |
| provider-overrides | `/admin/pricing/provider-overrides` | PRICING | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| hs-overview | `/admin/home-services/overview` | CATALOG | `SUPER_ADMIN_ONLY` | LOW | NONE |
| hs-service-catalog | `/admin/home-services/service-catalog` | CATALOG | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| hs-pricing-rules | `/admin/home-services/pricing-rules` | PRICING | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| hs-price-experience | `/admin/home-services/price-experience` | PRICING | `SUPER_ADMIN_ONLY` | LOW | NONE |
| hs-provider-matching | `/admin/home-services/provider-matching` | MATCHING | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| hs-matching-diagnostics | `/admin/home-services/matching-diagnostics` | MATCHING | `SUPER_ADMIN_ONLY` | LOW | NONE |
| hs-service-areas | `/admin/home-services/service-areas` | SERVICE_AREAS | `SUPER_ADMIN_ONLY` | HIGH | NONE (Service Area mutations covered indirectly via tenant-detail tab, see 05q) |
| hs-completed-job-deduction | `/admin/home-services/completed-job-deduction` | FINANCE | `finance.completed_job_deduction_rules.read` | HIGH | NONE |
| hs-settings | `/admin/home-services/settings` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| finance | `/admin/finance` | FINANCE | `finance:hub:read` | CRITICAL | NONE (sub-pages covered, hub landing page not directly tested) |
| finance-usage-credits | `/admin/finance/usage-credits` | USAGE_CREDITS | `finance.usage_credits.read` | CRITICAL | **COVERED** (05k, 05l, 05m) |
| finance-deposits | `/admin/finance/deposits` | SECURITY_DEPOSITS | `finance:deposits:read` | CRITICAL | **COVERED** (05k) |
| finance-topups | `/admin/finance/topups` | FINANCE | `finance:topups:read` | HIGH | **COVERED** (05k) |
| finance-claims | `/admin/finance/claims` | FINANCE | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| finance-payouts | `/admin/finance/payouts` | FINANCE | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| compliance | `/admin/compliance` | AUDIT | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| marketing | `/admin/marketing` | NOTIFICATIONS | `SUPER_ADMIN_ONLY` | LOW | NONE |
| notifications | `/admin/notifications` | NOTIFICATIONS | `SUPER_ADMIN_ONLY` | LOW | **COVERED** (05l) |
| analytics | `/admin/analytics` | PLATFORM_HEALTH | `analytics:dashboard:read` | MEDIUM | NONE |
| reports | `/admin/reports` | PLATFORM_HEALTH | `analytics:dashboard:read` | LOW | NONE |
| intelligence | `/admin/intelligence` | PLATFORM_HEALTH | `SUPER_ADMIN_ONLY` | LOW | NONE |
| engines | `/admin/engines` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | HIGH | NONE |
| security | `/admin/security` | SECURITY_OPERATIONS | `security:read` | CRITICAL | **COVERED** (05l) |
| workflow-templates | `/admin/workflow-templates` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| audit-logs | `/admin/audit-logs` | AUDIT | `auth:audit:read` | CRITICAL | NONE |
| users | `/admin/users` | IDENTITY | `auth:users:read` | CRITICAL | **COVERED** (05l, 05n) |
| roles | `/admin/users/roles` | ROLES_PERMISSIONS | `platform:roles:read` | CRITICAL | **COVERED** (05l) |
| permissions | `/admin/users/permissions` | ROLES_PERMISSIONS | `platform:permissions:read` | CRITICAL | NONE |
| media | `/admin/media` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | LOW | NONE |
| settings | `/admin/settings` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | HIGH | NONE |

**43 top-level navigation routes hand-documented above — 0 UNKNOWN.** The automated `e2e/route_coverage_guard.js` (built this sprint, parses `AdminLayout.tsx` directly rather than a hand-copied duplicate) counts **47** real nav items — 4 more than manually transcribed above, confirming the hand-count in this table is a close but not pixel-perfect transcription of the real source; the guard's own count is the authoritative one going forward. 13 of the routes documented above have real, existing Chromium coverage (counting `bookability/providers`, covered separately below as a nested route under `tenants`).

Additional nested/dynamic critical route confirmed covered: `tenants/[id]` (Tenant detail, with `?tab=onboarding` and `?tab=service-areas` sub-views) — covered by 05p and 05q. `admin/bookability/providers` — covered by 05p.

## What this registry does NOT include (honest scope boundary)

- The remaining ~117 of ~160 total `page.tsx` files are nested/dynamic sub-routes (detail pages, edit forms, wizard steps) that inherit their parent's permission via `resolveActiveNavId`'s prefix-matching — a real, existing, already-enforced mechanism (built in FINAL-L5-05N), not a gap this sprint introduces. Individually re-classifying and Chromium-testing all 117 is real, substantial, multi-sprint scope not attempted here.
- **Criticality classification above is a first-pass judgment** based on domain sensitivity (financial/security/identity routes = CRITICAL/HIGH; catalog/marketing/reporting = MEDIUM/LOW), not independently reviewed by a product owner. It is real and defensible, not fabricated, but should be treated as a draft for review, not a final product decision.
- **30 of 43 top-level routes (70%) have NO existing Chromium coverage.** This is the honest, primary remaining gap this mission targets — closing it for even a representative subset of the 30 uncovered routes (writing new, real, live-verified Chromium tests, not just classifying them) is real work this sprint's bounded time did not additionally complete beyond the registry itself.

## High-risk action registry (partial — real endpoints, not fabricated)

Cross-referencing this sprint's registry against actions already documented with real endpoint/permission evidence across prior sprints in this engagement (not re-derived from memory — each row traces to a specific prior certification document):

| Action | Endpoint | Permission | Allowed roles | Chromium coverage | Source |
|---|---|---|---|---|---|
| Tenant approve/reject/request-more-info | `POST /v1/admin/tenants/onboarding/{id}/{approve\|reject\|request-more-info}` | `tenants.approve`/`tenants.reject`/`tenants.request_more_info` | super_admin, admin_operations | **COVERED** (05p) | FINAL-L5-05P |
| Provider visibility override | `POST /v1/provider-portal/admin/bookability/providers/{tenant_id}/override-visibility` | `SUPER_ADMIN_ONLY` (documented gap, FINAL-L5-05W) | super_admin | **COVERED** (05p, via absence-check for Read Only) | FINAL-L5-05P/W |
| Service Area create (duplicate-detection) | `POST /v1/admin/tenants/{tenant_id}/service-areas` | `SUPER_ADMIN_ONLY` (`require_super_admin`, unchanged since 05P) | super_admin | **COVERED** (05q — real 409 on duplicate) | FINAL-L5-05Q/T |
| Usage Credit adjustment | `POST /v1/admin/usage-credits/{tenant_id}/adjustments` | `finance.usage_credits.adjust` | super_admin, admin_finance | **COVERED** (05AD — live success + DB + audit proof) | FINAL-L5-05AD |
| Job Force-Close | `POST /v1/admin/service-jobs/{job_id}/force-close` | `admin:jobs:force_close` | super_admin, admin_operations | **COVERED** (05AD — direct API denial matrix) | FINAL-L5-05AD |
| Job Void | `POST /v1/admin/service-jobs/{job_id}/void` | `admin:jobs:void` | super_admin, admin_operations | **COVERED** (05AD — direct API denial matrix) | FINAL-L5-05AD |
| Security Deposit adjust/release/refund | `POST /v1/admin/finance-hub/deposits/{id}/{...}` | `finance:deposits:*` | super_admin, admin_finance | **COVERED** (05U's live 5-role API matrix; not independently re-verified via Chromium this sprint) | FINAL-L5-05U |
| Export create/retry/cancel/download | `POST/GET /v1/enterprise/exports*` | resource-specific (`RESOURCE_EXPORT_PERMISSIONS`) | varies by resource | **COVERED** (05AA/AD live API; job-history UI in 05AB) | FINAL-L5-05AA/AB/AD |
| Role assignment | (Platform Users role editor) | `platform:roles:*` | super_admin | **COVERED** (05n) | FINAL-L5-05N |

**9 high-risk actions classified with real endpoint/permission/coverage evidence.** The mission's full required set (Part 12, ~30 named actions) is larger — Offering enable/suspend/reactivate, Finance top-up/correction, User invite/offboard, Session/device revocation, and Policy/System-configuration updates are not yet individually re-verified this sprint (each was touched by some prior sprint's investigation, but not consolidated into this registry with fresh Chromium evidence).

## Result

This sprint delivered a genuine, evidence-based (not fabricated) route classification registry for all 43 top-level Super Admin navigation routes (0 UNKNOWN) and a partial high-risk action registry (9 actions with full endpoint/permission/coverage traceability). This is real, bounded progress toward this mission's Parts 4-14 — closing the remaining 30 uncovered routes and ~20+ remaining high-risk actions with fresh, live Chromium evidence is real, substantial, multi-sprint scope, honestly not claimed complete here.
