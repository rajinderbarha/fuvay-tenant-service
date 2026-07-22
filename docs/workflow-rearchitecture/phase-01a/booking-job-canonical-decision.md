# Decision 1 — Canonical Booking and Job Pipeline

## Correction to initial Phase 1 assumption
Phase 1 flagged `Booking` (legacy) and field_ops `Job` as likely-dead parallel systems pending a caller check. **That check is now complete and disproves the assumption.** A targeted grep (SOURCE_VERIFIED, file:line evidence) found:

- `/v1/bookings` — actively called by `frontend/tenant-portal/lib/api.ts` (15+ call sites), `frontend/super-admin/lib/api.ts` (16+ call sites), `mobile/customer-app/src/lib/api.ts` (5 call sites).
- `/v1/admin/bookings` — actively called by `frontend/super-admin/lib/api.ts` (10 call sites).
- `/v1/jobs` (field_ops) — actively called by `frontend/tenant-portal/lib/api.ts` (20+ sites), `frontend/super-admin/lib/api.ts` (18+ sites), and `mobile/customer-app/src/lib/api.ts` (job get/approve/reject **and** a quote sub-path `/v1/jobs/{jobId}/quote` — meaning the mobile customer app's quote decision may be running through field_ops, not only through `quote_checklist`).
- `mobile/staff-app`'s `EarningsScreen.tsx` comment references `GET /v1/jobs/staff/{staff_id}/earnings` as "a REAL endpoint" it depends on — resolving Phase 1's open question about Earnings' backing endpoint, and confirming a fourth touch point on field_ops.

**None of `/v1/customer/jobs`, `/v1/customer/quotes`, `/v1/customer/invoices`, `/v1/tenant/finance` (the other field_ops paths Phase 1 flagged) are called anywhere** — so field_ops itself is only partially legacy: its core job/list/quote paths are live production dependencies, while its customer-facing quote/invoice/tenant-finance paths are genuinely unused.

## Revised lifecycle mapping

| Lifecycle stage | Record(s) actually in production use | Verification |
|---|---|---|
| Customer booking creation (current-gen booking flow, `BookingAssistant`→`BookingSuccess`) | `ServiceBooking`+`ServiceJob` via `final_records/confirm_router.py` | RUNTIME_VERIFIED |
| Booking list/detail views (tenant-portal `/bookings`, super-admin `/admin/bookings`, mobile `BookingsList`) | `Booking` (legacy engine) — this is what those specific screens actually read | SOURCE_VERIFIED (new) |
| Job list/detail + quote decision on mobile customer app | field_ops `Job` (`/v1/jobs`, including `/v1/jobs/{id}/quote`) | SOURCE_VERIFIED (new) |
| Provider matching, technician assignment, execution status, completion, commission deduction | `ServiceJob` via matching_engine → home_service_assignment → execution | RUNTIME_VERIFIED (unchanged from Phase 1) |
| Staff earnings (mobile) | field_ops (`/v1/jobs/staff/{id}/earnings`) | SOURCE_VERIFIED (new) |

**Conclusion: no single pipeline currently supports the full lifecycle end to end.** Three record types are simultaneously in production use for genuinely different current screens, not as accidental dead weight. This contradicts the Phase 1 draft's assumption and must be corrected.

## Revised disposition

| Record | Disposition | Reasoning |
|---|---|---|
| `ServiceJob` / `ServiceBooking` | **INTENDED CANONICAL TARGET** | Full execution-lifecycle support (matching → assignment → status → quote_checklist → completion → deduction → review), RUNTIME_VERIFIED at every stage. This is where new capability should be built. |
| `Booking` (legacy engine) | **COMPATIBILITY_READ_ONLY, NOT yet DEPRECATED** | Actively powers real, shipped list/detail screens today across all 3 apps that call it. Cannot be blocked or hidden without breaking those screens. Must remain fully functional (reads AND whatever writes those screens depend on) until each caller is migrated. |
| field_ops `Job` (core paths: list/detail/quote/earnings) | **COMPATIBILITY_READ_ONLY, NOT yet DEPRECATED** | Same reasoning — actively used, including the only confirmed backing for mobile staff Earnings and the mobile customer app's job-linked quote actions. |
| field_ops `Job` (unused paths: customer/quotes, customer/invoices, tenant/finance) | **LEGACY_BLOCK_NEW_WRITES candidate** | No caller found across all 5 apps — safe to restrict independently of the rest of field_ops. |

## Required compatibility layer / migration plan
1. **Do not touch or restrict** `/v1/bookings`, `/v1/admin/bookings`, or field_ops `/v1/jobs` core paths in Phase 2 — any of the "merge Jobs/Bookings/Appointments into one list" consolidation work in `page-consolidation-plan.md` must be re-scoped as an **API adapter**, not a data migration: build a read aggregation that presents `Booking` + field_ops `Job` + `ServiceJob` rows in one unified list view (BFF pattern, read-only), rather than assuming they're the same underlying data.
2. **Data migration requirement:** determine whether `Booking` rows and field_ops `Job` rows have any relationship to `ServiceJob` rows for the same real-world booking (e.g., shared external ID, timestamp correlation) — UNVERIFIED, needs a dedicated backend investigation before any true consolidation (not a Phase 2 frontend task).
3. **API adapter requirement:** the unified Jobs list (tenant_owner nav) and the Booking Exception Resolution workspace both need a BFF endpoint that reads from all three sources and normalizes status vocabulary for display — this is new backend work, tracked as a Phase 2 blocker below.
4. **Temporary restriction:** none — do not restrict any currently-called endpoint until its specific caller is migrated.
5. **Phase 2 frontend limitations:** the "merge jobs/bookings/appointments/service-jobs into one list" consolidation item from Phase 1 cannot ship as originally scoped (a single-source list). It must ship either as (a) a tabbed view showing each source separately with clear labels, or (b) deferred until the read-aggregation BFF (item 3) exists.
6. **Backend work required before Booking Exception Resolution workspace can be built:**
   - Confirm the actual relationship (if any) between `Booking`/field_ops `Job` rows and `ServiceJob` rows.
   - Decide whether `Booking`/field_ops `Job` screens should be migrated to `ServiceJob`-backed equivalents, or whether they represent a genuinely different booking type (e.g., an older non-home-services vertical) that legitimately coexists.
   - Build the read-aggregation BFF once the above is answered.

## Critical new evidence: an explicit adapter already exists between Booking and Job
A live runtime route dump (`scripts/workflow_rearchitecture/list_routes.py`, RUNTIME_VERIFIED) found:

`POST /v1/bookings/{booking_id}/convert-to-job`

This is a real, registered endpoint on the legacy `Booking` engine that explicitly converts a `Booking` into a `Job` (field_ops). This changes the picture from "three unrelated accidental parallel systems" to a **partially-understood, intentional two-stage pipeline for at least one flow**: `Booking` (intake/scheduling) → `convert-to-job` → field_ops `Job` (execution). Separately, the confirmed `ServiceJob` pipeline (`final_records` → `home_service_assignment` → `execution`) appears to be a **second, independent intake-to-execution path specific to the home_services vertical**, bypassing `Booking`/field_ops `Job` entirely (confirmed via `/v1/customer/home-services/booking-drafts/*` routes, which create a `ServiceBooking`/`ServiceJob` directly with no `Booking` or field_ops `Job` row involved).

**Working hypothesis (SOURCE_INFERRED, not fully confirmed):** ServiceOS may run two legitimate, parallel booking pipelines by design — an older, more general-purpose `Booking → convert-to-job → field_ops Job` pipeline (possibly serving non-home-services verticals, or an older generation of the product), and a newer, home-services-specific `ServiceBooking/ServiceJob` pipeline built end-to-end for the current vertical. If true, these are not "canonical vs legacy" in the simple sense — they may be **two canonical pipelines for two different scopes**, and forcing them into one navigation/workspace would be a modeling error, not a simplification.

**This hypothesis is not confirmed.** It is equally possible that `Booking`/field_ops `Job` is genuinely vestigial from an earlier product iteration and the `convert-to-job` endpoint is a compatibility bridge nobody has removed. Distinguishing these two possibilities is exactly the backend/product investigation this decision was already recommending — the new evidence sharpens the question but does not answer it.

## Decision status
**NOT CLOSED**, but meaningfully sharpened. Per the spec's explicit instruction ("If no single pipeline currently supports the full lifecycle, define the intended canonical target, required compatibility layer..."), this document defines that target and compatibility plan. The underlying question is now specifically: **is `Booking → Job` a legacy bridge for the same bookings `ServiceJob` handles, or a legitimately separate pipeline for a different scope (e.g. non-home-services verticals)?** This requires backend/product input — specifically, checking which vertical(s)/tenant configurations actually route through `Booking` vs `ServiceBooking` at creation time — before implementation. **The Booking Exception Resolution workflow (Decision 10.3) remains BLOCKED, per the spec's explicit instruction, until this is resolved.**
