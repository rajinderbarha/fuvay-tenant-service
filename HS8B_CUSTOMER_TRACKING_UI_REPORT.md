# HS8B — Customer Tracking UI Report

## Status: not built this pass — same established gap as HS7

No customer-facing web frontend exists anywhere in this repository (see
HS7's `HS7_CUSTOMER_BOOKING_UI_REPORT.md` — the actual customer surface,
`mobile/customer-app`, is disconnected from the real booking/tracking
API). This pass's time budget went to closing the two hard-gated HS8
blockers (parts approval, completion validation) plus real tenant and
technician UI, which had explicit `NOT_READY_*` failure codes of their
own in this ticket. Customer tracking UI was not attempted.

## What is real and verifiable without a UI
`GET /v1/customer/bookings/{booking_id}` correctly reflects the real job
status at every stage, live-verified through `completed` this pass (see
`HS8B_LIVE_PARTS_COMPLETION_UI_VERIFICATION_REPORT.md`), with no
internal score, usage-credit, or admin data ever present in the
response. A future customer UI has real, correct data to render against
— the gap is purely that no such UI exists yet.

## Verdict
Customer tracking UI: **not implemented.** Documented as a real,
un-fabricated gap, consistent with HS7's finding.
