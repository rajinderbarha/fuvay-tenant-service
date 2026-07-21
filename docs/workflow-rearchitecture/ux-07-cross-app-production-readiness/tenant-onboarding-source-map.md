# Tenant Onboarding Source Map — Round 2 (Workstream 7)

Traced from real frontend routes (`frontend/tenant-portal/lib/api.ts`) and
their real backend endpoints — not inferred from page names alone.

| Step | Frontend route | API endpoint | Notes |
|---|---|---|---|
| Registration initiate | `/register` | `POST /v1/public/register/initiate` | public, unauthenticated |
| Plan/package selection | `/register` | `POST /v1/public/register/confirm-plan` | |
| OTP/identity verify | `/register` | `POST /v1/public/register/verify` | |
| Payment order | `/register` | `POST /v1/public/register/payment-order` | package purchase, NOT job payment -- separate finance concept per this phase's hard constraints |
| Registration complete | `/register` | `POST /v1/public/register/complete` | creates the tenant + tenant_owner user |
| Onboarding status | `/(tenant)/onboarding-status`, `/(tenant)/setup/*` | `GET /v1/provider/onboarding/status` | real fields: `progress_percent`, `onboarding_ready`, `blockers[]`, `next_action` |
| Onboarding checklist items | `/(tenant)/setup/checklist` | `GET /v1/provider/onboarding/items` | itemized checklist entries |
| Refresh onboarding status | (button on the above) | `POST /v1/provider/onboarding/refresh` | recomputes status server-side |
| Package summary | `/(tenant)/packages`, `/(tenant)/finance/package` | `GET /v1/provider/onboarding/package-summary` | real fields: `has_package`, `status` (e.g. `pending_review`/`approved`/`activated`), `paid_at`/`approved_at`/`activated_at` timestamps, `included_credits` |
| Business profile / service area / category / offerings / pricing / staff | `/(tenant)/provider/service-setup`, `/service-areas`, `/services`, `/provider/offerings`, `/provider/pricing`, `/staff` | multiple `/v1/provider/*` endpoints (not individually re-traced this round beyond what Round 1 and this round's catalog/pricing checks already exercised) | see `catalog-entity-continuity.csv` / `pricing-continuity.md` for the ones actually exercised live |
| Platform review / approval | (super-admin side) `/admin/tenants/onboarding`, `/admin/tenants/[id]` | not traced this round (super-admin route inventory only; no live approval action attempted) | |

## Not traced this round (deferred)

Full form-field-level detail (every field on every step), the
approval/rejection/changes-requested UI presentation, and the exact
save-and-resume mechanics were not individually traced beyond the live
snapshot captured in `tenant-onboarding-live-verification.md`. This is a
real, disclosed scope boundary for this round — a full field-by-field trace
of ~15 onboarding steps across 2 apps was judged too large for this round's
remaining time budget after the install/typecheck/test baseline and role
verification work above.
