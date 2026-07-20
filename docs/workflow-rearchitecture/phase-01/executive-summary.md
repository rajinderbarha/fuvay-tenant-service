# Phase 1 — Workflow Rearchitecture: Executive Summary

**Scope:** Workflow simplification architecture only. No UI redesign, no backend logic changes, no frontend implementation in this phase.

## What we found

ServiceOS's backend is a code-based RBAC system (10 real roles) spread across ~140 router files in ~70 "engines." The platform grew by adding new engines rather than replacing old ones, so **several workflows have two or three parallel implementations** — some retired via `[DEPRECATED_410]` markers, several still fully live and reachable. The frontend (super-admin console, tenant-portal owner console, tenant-portal staff self-service, mobile customer app, mobile staff app) mirrors this: navigation is organized around engine names ("Home Services", "Field Ops", "Finance Hub") rather than user goals, and two of the five surfaces (super-admin nav, mobile customer app) have confirmed drift between what's built and what's navigable.

The core problem the user described — administrators and providers forced to understand backend structure instead of completing business tasks — is corroborated by evidence, not assumed:
- Booking has **3 parallel data models** (`Booking`/legacy, `Job`/field_ops legacy, `ServiceJob`/canonical) all still live at the API layer.
- Reviews has **2 parallel stacks** (`review` legacy table + `customer_reviews` canonical engine) both mounted.
- Finance/invoicing has **3 layered systems** (field_ops finance, invoice_payment Sprint 23, finance_hub) sharing the `/v1/admin/finance` prefix.
- Chat has **4 separate engines** (`chat`, `ai_chat`, `ai_conversation` x2, `platform_notifications` chat) with no single canonical messaging path.
- Super-admin's rendered sidebar and its own nav-config data file have drifted apart — ~10 real, working pages have no menu entry at all.

## Key numbers (see review-gate.md for the full checklist)

- **10 canonical roles** (RBAC-enforced): super_admin, tenant_owner, staff, technician, customer, guest, admin_operations, admin_finance, admin_security, admin_readonly. 6 additional "roles" referenced in a UI-facing config are aspirational/unimplemented.
- **~140 backend router files** inventoried; ~10 confirmed disconnected/dead, ~15 explicitly marked deprecated/410, ~20 flagged as duplicate/overlapping subsystems.
- **5 frontend surfaces**: super-admin console, tenant-portal owner console, tenant-portal staff self-service (web), mobile customer app, mobile staff app. ~154 admin pages, ~84 tenant-owner pages, ~16 staff-web pages, ~26 customer-app screens (+19 legacy nested screens), ~9 staff-app screens.
- **3 reference workflows** fully mapped end-to-end: Business Onboarding & Approval, Provider Service & Pricing Setup, Booking Exception Resolution.

## What this phase delivers

A workflow-first information architecture — role home pages, a "My Work" action queue per role, standard workspace patterns, and a full API-to-workflow coverage matrix — that hides the engine fragmentation above behind consistent, goal-oriented navigation. Every existing page receives a disposition (keep/simplify/merge/move/retire) with cited evidence. Nothing is implemented yet; this is the review artifact.

## Recommended immediate priorities once approved
1. Resolve the 3-way booking/job model split before building the "Booking Exception Resolution" workspace on top of it — the workspace needs one canonical record, not three.
2. Retire or hard-block the legacy `review` router now that `customer_reviews` is confirmed canonical (both are currently live and can diverge).
3. Fix the super-admin nav/route drift as a near-zero-risk quick win — it requires no backend change, just re-adding ~10 existing pages to the rendered nav config.

See `review-gate.md` for the full sign-off checklist and required decisions before Phase 2 begins.
