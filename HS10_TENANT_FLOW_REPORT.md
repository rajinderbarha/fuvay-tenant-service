# HS10 — Tenant Flow Report

## Verified this session (live)
- Service area coverage (`tenant_service_area_services` +
  `tenant_service_areas`) — real, live-verified throughout HS5B-HS10.
- Bookability computation (`_evaluate_provider_bookability`,
  `POST /v1/provider/status/refresh`) — real, live-verified repeatedly
  (HS6B, HS7, HS9B), including the credit-balance gate this session
  newly confirmed end-to-end.
- Jobs appearing after booking (`GET /v1/provider/service-jobs/assignable`)
  — real, live-verified in HS8 (after fixing the tenant-ID-scoping bug).
- Usage credit balance visibility with correct labels
  (`GET /v1/provider/usage-credits/balance`) — real, live-verified in
  HS9/HS9B; frontend page fixed in HS9B (was wired to a disconnected
  legacy "wallet" endpoint).
- Parts request approval (tenant-side) — real, live-verified in HS8B.

## Not verified this session
- `/tenant/setup/checklist`, `/tenant/setup/business-profile`,
  `/tenant/setup/service-areas`, `/tenant/setup/services`,
  `/tenant/setup/availability` — assumed pre-existing/working from
  HS4/HS4B/HS5/HS5B, not re-exercised this session.
- "Tenant sets provider price ranges inside admin range" /
  "type-specific brand overrides" — assumed working from HS3/HS4B, not
  re-tested this session (the pricing *resolution* logic these depend
  on was re-verified via the deduction/matching specificity tests, but
  the tenant-facing setup UI enforcing the range itself was not
  re-clicked-through).

## Verdict
Tenant backend data layer touched this session: **real and correct.**
Earlier-sprint tenant setup UI: **not re-verified**, assumed still
correct per its prior certification.
