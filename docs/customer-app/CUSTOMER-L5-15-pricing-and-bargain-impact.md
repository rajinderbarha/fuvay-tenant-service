# CUSTOMER-L5-15 — Pricing and Bargain Impact

## Finding

No reschedule capability exists for the canonical pipeline (see
`reschedule-policy-contract.md`), so there is no real code path that
revalidates or revises price/bargain state as a consequence of
rescheduling. CUSTOMER-L5-09's pricing engine and CUSTOMER-L5-10's
bargain engine remain exactly as those sprints documented them
(pricing: real, tier-based; bargain: entire manual-negotiation model
feature-flagged off) — neither is invoked from any cancellation or
reschedule orchestration, because no such orchestration exists.

## Parts-request / quote conflict on cancellation

`app/engines/quote_checklist/`'s real `cancel_quote` method
(`quote_service.py` lines 427–443) exists and is fully functional, but is
never invoked from `execution/home_service_service.py`'s `cancel_job`.
An open `ServiceJobQuote` (CUSTOMER-L5-14's real additional-cost
decision) or `PartsRequest` (the orphaned execution-engine model,
CUSTOMER-L5-14's other finding) is left completely untouched by a job
cancellation — no automatic cancel, no conflict error, nothing.

## This client's behavior

Since this client has no cancellation/reschedule trigger, there is no
in-app moment where a stale price, bargain, or quote could be presented
alongside a cancellation/reschedule action — CUSTOMER-L5-09's pricing
screen, CUSTOMER-L5-10's bargain screen, and CUSTOMER-L5-14's
quote-decision screen remain entirely independent, reachable only through
their own sprints' own flows, never through a cancellation/reschedule
path that does not exist.
