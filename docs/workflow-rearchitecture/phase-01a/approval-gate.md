# Approval Gate — Phase 1A

**No implementation, navigation change, or backend change has occurred in this phase.** All 20 files in `docs/workflow-rearchitecture/phase-01a/` are decision-closure analysis only.

## Decisions closed
2 (Review subsystem), 3 (Finance capability ownership — including the Phase 1 security-deposit blocker, now resolved), 5 (Parts/quote scope), 6 (Role navigation sign-off), 7 (Page consolidation), 8 (My Work contract), 9 (Next-action contract), 10.1 (Business Onboarding & Approval), 10.2 (Provider Setup).

## Decisions still blocked/open
- **Decision 1 (Booking/job canonical pipeline) — NOT CLOSED.** Verification proved `Booking`, field_ops `Job`, and `ServiceJob` are simultaneously live in production, not a legacy-vs-canonical split as assumed. Requires a dedicated backend investigation into whether these represent the same real-world bookings.
- **Decision 4 (Chat) — partially open.** Staff/technician and provider domains are solid; AI conversation domain (`ai_chat` vs `ai_conversation`) has a confirmed real duplication needing a product call; admin support chat's owning engine needs a quick confirmation. None of this blocks Phase 2.
- **Decision 10.3 (Booking Exception Resolution) — BLOCKED**, formally deferred to Phase 3, contingent on Decision 1.

## Canonical booking/job model
No single pipeline supports the full lifecycle today. Intended target: `ServiceJob`/`ServiceBooking` (proven to support the entire execution lifecycle — matching, assignment, status, quote, completion, deduction, review — end to end, RUNTIME_VERIFIED). `Booking` (legacy) and field_ops `Job` are both **actively used in production today** for booking-list/job-list/quote/earnings screens across tenant-portal, super-admin, and mobile-customer-app — they are compatibility layers, not dead code, and cannot be retired or hidden without breaking shipped features. A live route dump additionally found `POST /v1/bookings/{booking_id}/convert-to-job` — an explicit, already-built adapter between the two legacy systems — which sharpens (without yet answering) whether `Booking→Job` covers the same real-world bookings as `ServiceJob`, or a genuinely separate scope (e.g. a non-home-services vertical).

## Canonical review model
`customer_reviews` — confirmed canonical and confirmed already what the frontend uses. Legacy `review` engine's `POST /v1/reviews` create endpoint is live but has zero frontend callers; safe to block server-side with no discovered frontend impact.

## Finance capability owners
15 capabilities mapped in `finance-capability-ownership.csv`. All resolved to one canonical endpoint/service except `TenantPackagePurchase`'s exact retirement status (low-risk, non-blocking follow-up). Security deposit resolved: `finance_hub`'s `/v1/admin/finance/deposits*` is the confirmed live replacement for the 410'd legacy endpoints.

## Chat domain owners
Staff/technician messaging → `platform_notifications` staff_chat_router (strongest evidence — 2 apps + explicit in-code migration comment). Provider messaging → `platform_notifications` provider_chat_router. Core customer/tenant messaging → `chat/router.py` (reversed from Phase 1's dead-code mismarking). AI conversation domain unresolved between `ai_chat` and `ai_conversation` (both live, same app, likely two distinct features — needs a product decision, non-blocking).

## Parts workflow disposition — REVERSED from initial finding
A real `PartsRequest` entity (table `service_job_parts_requests`) with a full create/list/approve/reject/install endpoint set, linked to `ServiceJob.job_id`, was confirmed via live route registration dump and source read. **Parts Request/Approval is a genuine, buildable Phase 2 capability**, surfaced as a panel within the technician's "Inspection and Quote" nav item (not a 6th top-level nav item, to respect the approved 5-item technician nav cap). One follow-up remains non-blocking: confirming the customer-facing approval path for requests flagged `customer_approval_required=true`.

## Final primary navigation by role
- **super_admin:** Home, My Work, Businesses, Services, Operations, Finance, Governance, Reports, Settings (9 items, matches approved max list)
- **admin_operations/finance/security/readonly:** same shell, permission-filtered subset
- **tenant_owner:** Home, My Work, Jobs, Services, Team, Customers, Business, Credits, Settings (9 items, matches approved target list)
- **staff (Provider Manager):** Home, My Work, Jobs, Team, Quotes, Customers, Business (7 items, matches approved target list)
- **technician:** Today, My Jobs, Inspection and Quote, Work Completion, Profile (5 items, matches approved target list)
- **customer:** Home, Book, My Bookings, Quotes, Finance, Profile (6 items)

## Final visible page count by role (primary nav entries, post-consolidation)
super_admin: 9 top-level (down from ~40+ scattered entries, rest as DETAIL_TAB). tenant_owner: 9 top-level (down from ~30). staff: 7 (shared shell). technician: 5 (down from ~11 web + separate mobile set). customer: 6 (unchanged, already lean).

## Pages moved to tabs
~35 super-admin pages (Finance Hub's 10, Governance's 8, Services/Pricing's 4, Home Services' 9, Business Approval's 2, Complaints' 1). ~15 tenant-portal pages (Setup Wizard's 5, Business 360's 4, Credits' 3, Staff Profile's 4).

## Pages moved to drawers
None identified as requiring the drawer pattern specifically in this pass — the existing component patterns favor tabs; drawers reserved for future contextual quick-actions, not part of Phase 2 scope.

## Pages moved to Advanced
Staff web profile's documents/sessions/activity/notifications (4 pages). Mobile-staff notifications (1 screen).

## Pages retired (nav entry removed, code kept per rule 7)
`/provider/reviews`, `/provider/marketing`, `/provider/chat` (tenant-portal duplicates), `/staff/home-services/jobs` (confirmed duplicate of `/staff/jobs`). **Correction from initial draft:** `/admin/bookings`, `/bookings`, `/appointments` were NOT retired — verification proved active production use; they are kept as labeled sub-tabs instead.

## Required aggregation endpoints
5, unchanged from Phase 1: `GET /v1/{role}/my-work`, `GET /v1/admin/businesses/{id}/approval-summary`, `GET /v1/tenant/setup-progress`, `GET /v1/{role}/service-jobs/{id}/360`, `GET /v1/admin/finance/tenant-risk-summary`. Plus one new item identified in Phase 1A: a read-aggregation BFF over `Booking`+field_ops `Job`+`ServiceJob` for the Jobs list, contingent on Decision 1.

## Backend blockers before Phase 2
None that block Phase 2 itself. Two items block Phase 3 only (Booking/Job/ServiceJob relationship investigation, and the resulting read-aggregation BFF). Several low-priority non-blocking reconciliations listed in `backend-blockers.md`.

## Exact Phase 2 implementation scope
Navigation/route reconciliation → aggregation endpoints → My Work + next-action presentation → role-specific nav shells → page consolidation (tabs/merges, with Jobs list shipping as labeled sub-tabs, not a true merge) → Business Onboarding & Approval workflow → Provider Setup wizard → Advanced-page relocation → non-canonical entry-point removal. Booking Exception Resolution explicitly excluded from Phase 2, deferred whole to Phase 3. Full detail in `phase-02-scope.md`, `phase-02-implementation-order.md`, `phase-02-acceptance-criteria.md`, `phase-02-risk-register.md`.

## Tests or validations run
- Built `scripts/workflow_rearchitecture/list_routes.py` (read-only; no data mutation, no server bind) and ran it against the live `app.main:app` object, recursively resolving FastAPI's `_IncludedRouter` wrapper to enumerate all ~2,321 actually-registered routes (vs. only 5 visible via a naive `app.routes` walk).
- Confirmed via live route dump: `/v1/bookings` (21 routes incl. `convert-to-job`), `/v1/admin/bookings` (10 routes), `/v1/jobs` field_ops (48 routes incl. quotes/parts/earnings sub-paths), `/v1/reviews` legacy (15 routes incl. live `POST` create), `/v1/admin/reviews` canonical (8 routes), `/v1/customer/home-services/booking-drafts` (13 routes, independent of Booking/Job), `/v1/staff/service-jobs` (23 routes incl. `parts-requests`), `/v1/customer/quotes` (4 routes), `/v1/customer/service-jobs` (1 route).
- Read `app/engines/execution/models.py` and `home_service_service.py` source directly to confirm the `PartsRequest` model's fields and status machine, rather than relying on route paths alone.
- A prior sub-agent pass (before this session) grepped all 4 frontend/mobile codebases for legacy-endpoint callers, chat-prefix usage, and the `/admin/reviews` page's actual API target — that static evidence is retained and cross-checked against this session's runtime route dump; no contradictions found between the two passes.
- Did not run the existing pytest suite in this pass (out of scope for a read-only architecture-decision task; the route-registration dump was judged the highest-value runtime check achievable without touching business logic or data).

## Remaining unverified findings
- Whether `Booking`/field_ops `Job` rows correspond to the same real-world bookings as `ServiceJob` rows, or a separate scope (Decision 1's core open question).
- Which vertical/tenant configuration actually routes new bookings through `Booking` vs `ServiceBooking` at creation time.
- The customer-facing endpoint (if any) for approving a `PartsRequest` flagged `customer_approval_required=true`.
- Which engine backs `/v1/admin/chat/threads` (core `chat` admin routes vs `platform_notifications` admin_chat_router) — Domain 4 of the chat decision.
- Whether `ai_chat` and `ai_conversation` are one product feature or two intentionally distinct ones.
- Exact Tenant onboarding status-transition gating rules (carried over from Phase 1, still not traced to service-layer code).
- Whether any pre-L5-13 rows exist in the legacy `reviews` table without a `customer_reviews` counterpart (would require a data migration before blocking legacy writes).
- Complaint→job foreign-key target (SOURCE_INFERRED only, not traced to the model definition).

---
**Stopping here. Awaiting approval before any Phase 2 implementation begins.**
