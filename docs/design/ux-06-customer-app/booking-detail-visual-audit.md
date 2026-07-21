# Booking Detail Visual Audit — UX-06 Round 5 (Workstream 9)

Rewritten this round (see the file's own header comment for the full
rationale). Real production nav (Bookings tab → tap a card → Booking Detail).

**Two real defects found and fixed, not just typecheck cleanup:**
1. The screen previously rendered a fabricated "Payment Breakdown" card using
   fields (`quoted_price`, `credit_applied`, `payable_amount`) never confirmed
   to exist on the real `Booking` response — removed, replaced with the
   standard real on-site-payment note.
2. The screen had a full "Cancel Booking" flow calling `bookingsApi.cancel`,
   which was **never a real export** — cancellation for this pipeline is
   deliberately unresolved/unexposed per the canonical domain rule
   established in Round 1. This was a genuine rule violation (a dead control
   calling a nonexistent endpoint) that Round 4's screen inventory had not
   caught — removed entirely this round, along with the QuoteApproval/
   JobTracking/Review CTA buttons that referenced fields not present on this
   real `Booking` shape.

Now shows only real, confirmed fields: `booking_number`, `status` (via the
existing `JobStatusBadge`), `service_type`, `scheduled_at` (with an honest
"Not yet scheduled" fallback), the internal `id` shown small/secondary
(never as the primary label, per Workstream 9), customer notes if present,
and the standard on-site-payment note.

**Not verified this round**: rendering against a REAL created booking (none
exists — see canonical-booking-live-evidence.md for why), dark theme (doesn't
exist), narrow-width/large-text scaling.
