# Canonical Decision Register — Phase 1A

Master index of all 10 decisions, their status, and the file with full detail. Read this first, then the linked file for anything not fully closed.

| # | Decision | Status | Detail file |
|---|---|---|---|
| 1 | Canonical booking/job pipeline | **NOT CLOSED** — reversed from Phase 1's tentative assessment. Verification proved `Booking` (legacy), field_ops `Job`, and `ServiceJob` are all 3 actively used in production. Intended target (`ServiceJob`) is defined, but the relationship between the 3 systems is unknown and requires a backend investigation before any true consolidation | `booking-job-canonical-decision.md` |
| 2 | Review subsystem | **CLOSED** — `customer_reviews` confirmed canonical, confirmed already what the frontend uses (Phase 1's flagged ambiguity was a false alarm). Legacy `review` engine's create endpoint is live but has zero frontend callers — safe to block | `review-canonical-decision.md` |
| 3 | Finance capability ownership | **CLOSED** for all 15 capabilities except one sub-item (`TenantPackagePurchase` vs `TenantPackageAssignment` legacy-sibling status, low-risk, non-blocking). Security deposit — flagged BLOCKED in Phase 1 — is now **RESOLVED**: `finance_hub`'s `/v1/admin/finance/deposits*` confirmed as the live canonical replacement | `finance-capability-ownership.csv` |
| 4 | Chat/communication ownership | **PARTIALLY CLOSED** — the 2 domains needed by the 3 reference workflows (staff/technician and provider messaging) are strongly resolved to `platform_notifications`. Core customer/tenant messaging resolved to `chat/router.py` (reversing Phase 1's mismarking). AI conversation domain has a confirmed genuine duplication requiring a product decision, non-blocking | `chat-domain-ownership.md` |
| 5 | Parts/quote scope | **CLOSED — REVERSED from initial finding.** Runtime route verification + source read proved a real `PartsRequest` model and full create/list/approve/reject/install endpoint set exist, linked to `ServiceJob`. Parts Request/Approval is a genuine, buildable workflow in Phase 2, not excluded | `quote-parts-scope-decision.md` |
| 6 | Role navigation sign-off | **CLOSED** — final nav per role produced, respecting the approved max-item lists for each role | `final-role-navigation-matrix.csv` |
| 7 | Page consolidation | **CLOSED**, with the Jobs-list consolidation explicitly descoped from "one merged list" to "labeled sub-tabs" pending Decision 1 | `page-consolidation-plan.md`, `final-page-disposition-matrix.csv` |
| 8 | My Work contract | **CLOSED** — implementation-ready schema defined, derives from existing records, no new state machine | `my-work-contract.md` |
| 9 | Next-action contract | **CLOSED** — canonical response shape defined for all 10 domains with stored/derived/aggregated/permission-filtered labeling | `next-action-contract.md` |
| 10.1 | Business Onboarding & Approval | **CLOSED, implementation-ready** | `business-onboarding-final-contract.md` |
| 10.2 | Provider Service & Pricing Setup | **CLOSED, implementation-ready** (with 2 non-blocking backend reconciliations noted) | `provider-setup-final-contract.md` |
| 10.3 | Booking Exception Resolution | **BLOCKED**, per spec's explicit instruction, pending Decision 1 | `booking-exception-final-contract.md` |

## Runtime validation performed in this pass
A read-only route-registration inspector (`scripts/workflow_rearchitecture/list_routes.py`) was built and run against the live FastAPI app object (`app.main:app`). It discovered that included routers are wrapped in FastAPI's `_IncludedRouter` dataclass, so a naive `app.routes` walk only surfaces 5 top-level routes (docs/openapi/static) — the script recurses through `.original_router` to reach the true ~2,321 registered endpoint routes. This is RUNTIME_VERIFIED evidence (routes as registered in the actual running app object, not just source grep) and it drove two corrections below. No database was touched, no server was bound, no data was mutated.

## What changed between Phase 1 and Phase 1A
Phase 1 flagged several items as UNVERIFIED and assumed the more optimistic resolution (legacy systems likely dead, security deposit likely broken, chat likely consolidated) pending a follow-up check. That check ran in Phase 1A and **reversed two of those assumptions**:
- Booking/Job/ServiceJob: proved to be a live 3-way split, not dead legacy weight — this is the most consequential finding in this document set and the reason Decision 1 and Decision 10.3 remain open/blocked.
- Security deposit: proved to already have a working canonical replacement — this is a downgrade of risk, not an escalation.
- Chat: proved more fragmented than inferred (core `chat` engine is alive, not dead; AI domain has real simultaneous duplication) but the 2 domains that matter for the reference workflows are solidly resolved.
- Review: Phase 1's hoped-for resolution was confirmed correct — no surprises here.

This is exactly the kind of correction this phase exists to catch before Phase 2 frontend work starts, rather than after.

**Two additional corrections from this pass's runtime validation:**
- **Decision 1 sharpened, not resolved:** a live `POST /v1/bookings/{booking_id}/convert-to-job` endpoint proves `Booking`→field_ops `Job` is an intentional bridge, not accidental duplication — but whether its scope overlaps with `ServiceJob`'s scope remains the open question.
- **Decision 5 reversed:** Phase 1 and the initial Phase 1A draft both incorrectly concluded no Parts Request/Approval entity exists. A real `PartsRequest` model, full endpoint set, and status machine were found via runtime route dump and source read. Parts UI is now in scope for Phase 2, not excluded.
