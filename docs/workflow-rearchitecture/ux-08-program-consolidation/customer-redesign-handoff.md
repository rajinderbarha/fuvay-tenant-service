# Future Customer Redesign Handoff

This document defines the functional contract each Customer screen must
preserve through a future visual redesign. Visual design, layout, spacing,
motion, and responsive behavior are all open for the redesign phase to
change freely. What follows must not be lost.

## Home

- **Must preserve**: location display + change control, notification
  control, profile access, real-first-name greeting with honest
  time-of-day fallback (never a fake name), search entry (opens SmartBot
  or real catalog search), a primary "Start with SmartBot" CTA, compact
  real popular-service tiles (no premature Repair/Service/Consult badges
  at this stage), real active-booking state (or an honest empty state --
  never fabricated), real recent-services with safe "Book again", a
  truthful (non-fabricated) trust-info row, exactly 5 bottom-nav tabs
  (Home/Bookings/SmartBot/Notifications/Profile) with non-wrapping
  labels.
- **Backend endpoints**: `bookingsApi`, `fieldOpsJobsApi`, `catalogApi`
  (see `mobile/customer-app/src/lib/api.ts`).
- **Design freedom**: full visual layout, color, spacing, iconography,
  card shapes, animation.
- **Future responsive requirement**: see `future-responsive-certification-plan.md`.

## SmartBot

- **Must preserve**: category context carried in from Home (never
  re-asking a category already chosen), exactly 3 conversation languages
  (English/हिन्दी/ਪੰਜਾਬੀ) via a one-tap control, one current
  question shown at a time in the real guided booking-flow modal,
  structured choice options sourced from real session state (not a
  hardcoded universal question set), minimal required typing (free text
  optional except where the real flow requires it), an optional photo
  attachment flow only where genuinely backend-supported, a compact
  progress indicator reflecting real conversation state, an editable
  compact answer summary, the existing real address/schedule/price/
  bargain/standard-price/confirmation steps, error recovery that
  preserves progress and never creates a duplicate booking.
- **Backend endpoints**: `aiConversationApi`, `homeServiceDraftApi`,
  `bookingConfirmApi` (see `lib/api.ts`).
- **Must-preserve behavior**: language switching preserves the
  conversation/category/answers; canonical IDs/enums/tool names are never
  translated; pricing stays server-authoritative; on-site payment only.
- **Design freedom**: full visual layout of the conversation body, card
  styles, progress-indicator style, color, motion (respecting
  reduced-motion).
- **Unsupported actions to keep hidden**: cancellation, rescheduling,
  any online-payment capture/escrow/payout.

## Screens requiring redesign review (functional contract, not full detail per Home/SmartBot above)

| Screen | Required data | Required actions | Backend endpoints | Must-preserve |
|---|---|---|---|---|
| Login | credentials | sign in | `/v1/auth/login` | real auth only, no fake success |
| Booking list | real bookings | view, tap-through | `bookingsApi` | real data only |
| Booking detail | real booking/job | view status/price/address; "Track your job" | `bookingsApi`, `fieldOpsJobsApi` | no fake cancel/reschedule action |
| Job tracking | real ServiceJob | view customer-safe timeline | `fieldOpsJobsApi` | no arbitrary status submission from customer app |
| Notifications | real notifications | view, tap-through | notifications endpoint | never fabricate notifications to fill empty state |
| Profile | real customer profile | view/edit, access Support (folded Chat) | profile endpoint, `chatApi` | real data only |
| Address book | real addresses | list/add/edit/(delete if supported) | address endpoints | no fabricated delete/default behavior |
| Review | real review submission | rate, submit | `POST /v1/customer/reviews` | frontend validation to prevent malformed submit; never use legacy `/v1/reviews` |
| Help/support | real support paths | FAQ, contact | as wired | no fake 24/7 or SLA claims |

## Explicitly NOT covered by this handoff

Quote approval, checklist, parts-request, and payment-methods screens are
intentionally excluded from redesign priority — their functional contracts
depend on unresolved backend tickets in `backend-contract-handoff.md` and
should be redesigned only after those are resolved, to avoid redesigning
around behavior that will change.
