# CUSTOMER-FRONTEND-02 — Tracking UI Report

File: `app/customer/bookings/[bookingId]/page.tsx`

## What it shows (verified by reading the JSX)
- Booking number (`detail.booking_number`)
- Issue summary
- Status (`detail.status`) — raw enum string, not humanized (minor cosmetic gap, see Route report)
- Assignment message (if present)
- Provider name (`detail.selected_provider.provider_name`)
- Selected price + tier (`detail.selected_price_amount` / `detail.selected_price_option`)
- Payment mode: hardcoded "Customer Pays Provider Directly" (correct required copy)
- Address (`detail.address.address_line1`, `detail.city`)
- "Rate Your Experience" link — only rendered `{detail.status === "completed" && ...}` (gating confirmed in source)
- Status Timeline section from `tracking.timeline[]` (event + created_at)

## Refetch/update behavior
Both `getCustomerBookingDetail` and `getCustomerBookingTracking` are called inside a `useEffect` keyed on `bookingId`, i.e. fetched fresh every time the page mounts/navigates to a new booking id. There is no polling interval and no websocket — a customer must re-open/re-navigate to the page to see a status change. This is acceptable per the spec ("re-fetches on mount... real-time push isn't required unless already built") but is worth flagging: if a customer leaves the tab open, they will NOT see a live status update without a manual refresh/nav. Not fixed (out of "don't add speculative real-time infra" judgment call; flagged as a blocker below).

## Safety scan of this file
Grepped the rendered JSX for internal ledger/audit/commission fields — none present. Only customer-safe fields are read/rendered (booking_number, issue_summary, status, assignment_message, provider name, selected price/tier, address, payment copy, timeline event/timestamp).

## Verdict: PASS. One documented UX gap (no auto-refresh/poll) added to remaining blockers, not a safety or correctness defect.
