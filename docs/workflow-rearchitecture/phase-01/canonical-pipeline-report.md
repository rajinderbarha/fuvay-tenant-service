# Canonical Pipeline Report — Competing Implementations

For each area: which implementation is canonical, which is legacy, and disposition. Verification levels per finding noted inline.

## 1. Booking / Job creation — THREE parallel models, all live
| Implementation | Table | Router | Status |
|---|---|---|---|
| `Booking` | `bookings` (+status_history, notes, reschedule_requests) | `booking/router.py` (`/v1/bookings`), `booking/admin_router.py` (`/v1/admin/bookings`) | **Legacy** — router docstring self-labels "Legacy / unchanged endpoints"; has `_run_legacy_preflight`. Still mounted (SOURCE_VERIFIED). |
| `Job` (field_ops) | field_ops tables | `field_ops/router.py` (`/v1/jobs`), `staff_router.py`, `customer_router.py` | **Legacy/parallel** — separate from both Booking and ServiceJob. Still mounted (SOURCE_VERIFIED). |
| `ServiceJob` | `service_jobs` | `home_service_booking` (draft) → `final_records/confirm_router.py` (creates ServiceJob) → `home_service_assignment` → `execution/home_service_router.py` | **Canonical** — confirmed by repo history (L5-13 memory), RUNTIME_VERIFIED via HS7/HS8/HS10 live tests. |
**Decision needed:** confirm whether `/v1/bookings` and `/v1/jobs` still have live frontend callers; if not, retire. Current frontend inventory found no direct field_ops/legacy-booking calls in the 5 audited apps, suggesting these routers may be backend-only dead weight, but this needs explicit confirmation before removal (UNVERIFIED - not confirmed zero callers).

## 2. Quote / approval
Canonical: `quote_checklist` engine (customer-side approve/reject/revise). No competing implementation found; `field_ops/customer_router.py`'s nested `quote_router` (`/v1/customer/quotes`) is a parallel, older surface tied to the legacy `Job` model — same naming collision risk as booking. SOURCE_VERIFIED.

## 3. Parts approval
No canonical implementation exists. `POST /v1/staff/service-jobs/{id}/parts-required` only flips job status to `quote_required`; there is no structured parts-request/approval entity. This is a genuine gap, not a duplicate-implementation problem (SOURCE_VERIFIED, HS8_PARTS_REQUEST_REPORT.md).

## 4. Pricing
Canonical: `pricing` engine, Low/Mid/High automatic options computed post-matching. Legacy: `BargainRule`/`bargain_engine.py` (manual bargain) — model kept, business logic retired via feature flags (`manual_bargain_rules_enabled=False`), admin UI shows deprecated banner rather than being deleted. RUNTIME_VERIFIED.

## 5. Credits / Commission
Canonical: `usage_credits` engine ("FINAL-L5-05J — Canonical Usage Credit Engine"), older credit paths in `package_commerce` explicitly marked "(legacy path)" but still functional as thin redirects. `platform_commerce`'s wallet-deduct endpoint explicitly `[DEPRECATED]`, superseded by Completed Job Deduction. RUNTIME_VERIFIED.

## 6. Provider onboarding
Canonical: `tenant_engine` onboarding flow (`/v1/tenants/onboarding/signup` → admin review/activate). No competing implementation found in this pass. SOURCE_VERIFIED but UNVERIFIED end-to-end (this pipeline fell outside the audited HS/PHASE report set — flagged for follow-up, see workflow-gaps-and-blockers.md).

## 7. Category / service catalog
Two "setup templates/bulk wizard" systems found: `admin_catalog/service_setup_template_router.py` + `bulk_setup_router.py` (Sprint 34F/34H) vs `service_setup/templates_router.py` + `bulk_router.py` (migrations 091/098). Neither is marked deprecated. **Needs manual reconciliation** — SOURCE_VERIFIED (duplication exists), UNVERIFIED (which is canonical).

Two "customer flow" systems similarly duplicate: `admin_catalog/customer_flow_router.py` (Sprint 34J) vs `customer_flow/router.py`+`admin_router.py` (Sprint 14). Same disposition.

## 8. Role management
No competing implementation — single code-based RBAC (`app/core/permissions.py`), no DB-driven roles table. `roles_permissions` engine is a read-only UI layer over it; role/permission mutation is not yet wired to any backend effect (SOURCE_VERIFIED, explicit code comment).

## 9. Media / profile photo upload
Not investigated in this pass — flagged as UNVERIFIED, follow-up needed.

## 10. Reviews
Canonical: `customer_reviews` engine (Sprint 24). Legacy: `review/router.py` on orphaned `reviews` table — **still fully mounted and reachable at `/v1/reviews/*`**, not merely dead code. This is the single highest-risk duplicate in the system: two live write paths for the same conceptual entity. RUNTIME_VERIFIED (customer_reviews is what job-completion rating writes to, per L5-13); review/router.py's continued mounting is SOURCE_VERIFIED.

## 11. Chat
Four separate engines mounted: `chat/router.py` (core), `ai_chat/router.py`, `ai_conversation` (Sprint 15 + Sprint 29 hardening), `platform_notifications` chat sub-routers (Sprint 27). No single canonical real-time messaging path is documented. SOURCE_VERIFIED (all mounted); UNVERIFIED which the frontends actually use predominantly — frontend audit shows staff-app and tenant-portal both call `/v1/staff/chat/threads` (platform_notifications-family), suggesting that one is the operationally canonical path for staff↔customer chat, but this is inferred, not confirmed against ai_chat/ai_conversation usage.

## 12. Finance/Invoicing
Three layered systems share `/v1/admin/finance`: `field_ops` finance (oldest), `invoice_payment` (Sprint 23), `finance_hub` (newest — mounted first in main.py to deliberately win the `/summary` collision). `finance_hub` is treated as canonical per an explicit main.py comment. field_ops's older `/v1/customer/invoices` path is likely legacy relative to invoice_payment's `/v1/customer/service-invoices`. SOURCE_VERIFIED.

## Disposition summary
| Area | Canonical | Legacy/dup kept live | Recommended action |
|---|---|---|---|
| Booking/job | ServiceJob | Booking, field_ops Job | Confirm zero frontend callers, then retire |
| Reviews | customer_reviews | review/router.py | Retire — highest priority, active data-integrity risk |
| Quotes | quote_checklist | field_ops quote_router | Confirm caller, retire if unused |
| Chat | platform_notifications (inferred) | chat, ai_chat, ai_conversation x2 | Needs explicit product decision on canonical messaging engine |
| Finance | finance_hub | field_ops finance, invoice_payment (partial) | Consolidate under finance_hub, keep invoice_payment's job-level invoicing |
| Setup templates | UNVERIFIED | admin_catalog vs service_setup | Manual reconciliation required |
| Customer flow | UNVERIFIED | admin_catalog vs customer_flow | Manual reconciliation required |
| Brands | admin_catalog/brand_*router.py | brands/*_router.py (never mounted) | Delete dead code, zero risk |
