# CUSTOMER-L5-08 — Availability Contract

## There Is No Customer-Visible Availability State

The spec's aspirational model anticipated a discrete availability signal
(e.g. "Available now", "Available tomorrow", earliest-slot time). This does
not exist anywhere in the real matching response. Availability is folded
into a single internal boolean eligibility gate:

- `provider_visibility_statuses.is_bookable` — a precomputed column, an
  in-code comment on `_passes_full_eligibility_gate()`
  (matching_engine.py) explicitly states it already consolidates what were
  previously separate technician/availability/package/wallet/deposit
  checks into this one canonical flag.
- A provider that fails this gate is simply excluded from the candidate
  pool before scoring — the customer never learns *why* a specific
  provider was unavailable (indeed, the customer never learns any excluded
  provider existed at all — only the single winner or a generic no-match
  outcome).

## Break/Holiday/Booking-Window Checks Are Real But Currently Dead in This Flow

`_passes_full_eligibility_gate()` has a block for break/holiday/
booking-window checks, but it only runs `if requested_at is not None` —
and the customer router (`match_and_price`) never passes a `requested_at`
value (there is no real UI concept of "book for this exact date/time" in
this flow; only the free-text `preferred_time_window` from CUSTOMER-L5-07
exists, and it is never forwarded into the matching call). This means
these specific checks are real, working code, but structurally unreachable
from this client's real call pattern today — documented as a known gap
rather than a feature this sprint could have wired up (wiring it would
require the matching endpoint to accept a `requested_at` parameter it
currently does not, which is a backend contract change out of this
sprint's scope).

## No Earliest-Available-Time Field

No such field exists in `selected_provider` or anywhere else in the
response. Not fabricated to make the preview screen feel more complete.

## Client Behavior

Since there is no availability signal to render, `ProviderPreviewScreen`
shows no availability-related UI element at all — no spinner-then-badge for
"checking availability", no calendar, no time-slot picker. The five real
fields (provider-preview-contract.md) are the entire preview; anything
implying a richer availability model would be a fabrication.
