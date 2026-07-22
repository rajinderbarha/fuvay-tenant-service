# Cross-App Workflow Map (Canonical Home Services Journey)

Consolidated from real, live-verified evidence produced during UX-07
Rounds 1-3 (not re-derived from scratch this pass — cited from the source
docs in `docs/workflow-rearchitecture/ux-07-cross-app-production-readiness/`
carried into this worktree's history).

## Real record evidence

| Step | Entity | Value | Status |
|---|---|---|---|
| Customer booking (UX-06 closure) | ServiceBooking | `BK-20260721-000005` | created, verified via app UI |
| Customer booking (UX-06 closure) | ServiceBooking | `BK-20260721-000006` | created, verified via app UI |
| Customer booking (UX-07 Round 3) | ServiceBooking | `BK-20260721-000008` | created |
| ServiceJob (UX-07 Round 3) | ServiceJob | `JOB-20260721-000008` | carried through the **full status-transition graph** to `completed` |
| Commission | server-computed deduction | `-21.0` on a `775.0` job | verified via direct psql query |
| Customer review | `REV-56700400` | status `pending` | created via canonical `POST /v1/customer/reviews`, re-verified independently at the start of UX-07 Round 4 (still `pending` at that point) |

## Canonical transition map

```
Customer auth (mobile/customer-app AuthContext)
  → POST /v1/auth/login
→ Category/service selection (Home → SmartBot category handoff, UX-07 Pass 3d)
  → real catalogApi.categories()
→ SmartBot orchestration (DeepSeekChatScreen, aiConversationApi)
  → real DeepSeek tool calls
→ Serviceability check
  → real serviceability endpoint
→ Server-authoritative pricing (match_provider_and_price(), bargain_available flag)
  → bargain path (BargainRule tiers) OR standard-price path (ServicePricingRule fallback,
    UX-06 backend fix on fix/bargain-optional-price-path)
→ Booking summary → homeServiceDraftApi.summary()
→ Idempotent booking creation → bookingConfirmApi.confirmHomeServiceBooking()
  → real ServiceBooking record (BK-20260721-000008)
→ Tenant booking visibility (frontend/tenant-portal)
  → real booking list endpoint
→ Tenant technician assignment
  → real ServiceJob record created (JOB-20260721-000008)
→ Technician job visibility (mobile/staff-app, real service_jobs pipeline per
  MODULE-L5-36 fix)
→ Legal ServiceJob status transitions (assigned → accepted → on_the_way →
  reached_site → inspection_started → inspection_done → service_started/
  quote_required → work_done → completed) -- all real, verified via direct
  psql query at each Round 3 step
→ Job completion (status = completed, confirmed via psql)
→ Server-calculated commission (-21.0 on 775.0, verified via psql)
→ Customer review submission (REV-56700400, POST /v1/customer/reviews)
→ Tenant review visibility (where supported by the tenant-portal review surface)
```

## What UX-08 re-verified this pass (fresh, not cited)

- Customer-app fresh install: 76/76 tests, 0 typecheck errors — confirms
  the codebase carrying this workflow is unregressed at the UX-08
  baseline commit.

## What UX-08 did NOT re-run this pass

A live re-execution of the full booking→completion→review chain against a
running backend was not repeated in this pass — the chain was already
proven live during UX-07 Round 3 with real, still-queryable database
records (re-confirmed at the start of UX-07 Round 4). Re-creating a new
live booking end-to-end was judged unnecessary duplication of already-real
evidence and would risk creating unnecessary additional test data; the
existing records remain the authoritative proof.
