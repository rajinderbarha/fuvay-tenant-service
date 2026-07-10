# Type-Dependent Brand Pricing — Tenant UI Report

## Not built this sprint
`/tenant/setup/services` (`frontend/tenant-portal/app/(tenant)/tenant/
setup/services/page.tsx`) already calls the brand-pricing endpoints with
a `service_type_id` context in its per-type/brand pricing table layout
(confirmed via the earlier HS0 sprint's inspection of this file — the
UI already presents pricing grouped by type). Whether the frontend
already passes `service_type_id` correctly on every brand-pricing
call, and whether its table clearly labels brand overrides under their
type (per the ticket's "Wrong tenant UI" vs "Correct tenant UI"
examples), was **not re-verified against the current file this
sprint** — this sprint's testing was done entirely via direct API calls
(curl) against the real backend, not through the rendered frontend.

## What is confirmed backend-correct (which the frontend now benefits from automatically)
Because the frontend already threads `service_type_id` through its
existing API calls (per the router signature, which was not changed
this sprint — only the underlying storage was), the frontend should
already receive genuinely independent per-type brand pricing without any
frontend code changes, once the backend fix (this sprint) is deployed.
This was not visually confirmed in a browser (dev server was not
started this sprint — see Remaining Blockers).

## Verdict
Tenant UI: **not independently re-verified this sprint**. The backend
fix is transparent to the frontend's existing API contract, so no
frontend code changes were required or made — but a live browser check
was not performed to confirm the UI displays the newly-independent
per-type brand prices correctly.
