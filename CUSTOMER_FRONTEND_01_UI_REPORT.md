# CUSTOMER-FRONTEND-01 — UI Report

## Design system
`frontend/customer-app/styles/globals.css` is a new, dedicated stylesheet (not shared
with tenant-portal at build time, since these are two separate Next.js apps with
separate package.json/node_modules) that reuses tenant-portal's light-mode CSS
variable values (`--bg`, `--surface`, `--border`, `--brand`, `--success`,
`--warning`, `--danger`, `--info`) verbatim from `frontend/tenant-portal/styles/globals.css`,
plus a dark-mode block and `data-theme` overrides per the artifact/design-system
convention used elsewhere in this repo. Consumer-specific additions: `.co-bottom-nav`,
`.co-nav-fab` (floating center CTA), `.co-chip` (selection chips), `.co-price-card`
(Low/Mid/High cards with `.co-badge-recommended`), `.co-progress-track` (stepper).

## Layout
- `app/layout.tsx` — root shell, imports globals.css.
- `components/BottomNav.tsx` — Home / Services / floating Book Now / Bookings / Profile,
  active item highlighted via `usePathname()`.
- Header pattern (avatar/name/greeting/notifications/booking-history shortcut) is
  implemented inline in `app/customer/home-services/page.tsx` rather than as a shared
  component, since only that page needs the full greeting header; the booking wizard
  and detail pages use a simpler step-title header instead.

## Landing page (`/customer/home-services`)
Greeting + search input + category chip-cards (queried live from
`/v1/catalog/master/categories`, filtered to `is_customer_visible !== false`) +
loading skeletons (`.co-skeleton`) + empty state. "Popular services" and "recent
booking" widgets from the spec were NOT built as separate sections — there is no
backend endpoint for "popular services" or a customer's single most-recent booking
distinct from the full bookings list, so building them would have meant either
fabricating data or re-deriving it client-side from the full list, which was judged
lower priority than the core 16-step booking flow given the time available. This is
a real gap, documented in CUSTOMER_FRONTEND_01_REMAINING_BLOCKERS.md, not a fake
placeholder.

## Booking wizard (`/customer/home-services/book`)
Single stateful page implementing the 7-step stepper (Service → Details → Location →
Provider → Price → Review → Confirm) with a `co-progress-track` progress bar,
back/next validation gates matching the HARD RULE (provider selected before price
finalized; booking uncreatable without both).

## Responsive behavior (code-level review, no real device lab — see Browser Verification Report)
- `.co-container { max-width: 480px }`, widened to 600px at `min-width: 768px`.
- `html, body { overflow-x: hidden }` guards against horizontal overflow.
- Price cards (`.co-price-card`) are block-level, stacked vertically by default at all
  widths (no manual grid breakpoint needed since the design is a single column).
  Bottom nav is `position: fixed` with `max-width` matching the container so it stays
  usable on desktop widths too.
- Buttons (`.co-btn-primary`/`.co-btn-secondary`) use `padding: 14px 20px` and
  `width: 100%` for large mobile tap targets.
