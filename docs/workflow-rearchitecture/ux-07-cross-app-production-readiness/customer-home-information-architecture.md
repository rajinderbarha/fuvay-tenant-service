# Customer Home — Information Architecture (UX-07 Pass 3d)

## Structure (top to bottom)

1. **Top utility row** (brand-navy, fixed): saved-location chip (honest
   placeholder "Choose service location" — no real saved-address-summary
   endpoint was found wired to Home in `api.ts`'s `addressApi`, so this
   opens `AddressBook` rather than fabricating a location string),
   notification bell (routes to the new Notifications tab), profile avatar
   (real first-initial from `AuthContext`, or `?` when not loaded).
2. **Greeting** — real first name from `AuthContext.user.full_name` when
   present; time-of-day-only when not. Never a fake name.
3. **Search entry** — `TextInput` with placeholder "Search AC repair,
   plumbing, cleaning…"; submitting hands the raw query text to SmartBot as
   `initialCategoryLabel` (see `category-smartbot-handoff.md`) rather than
   rendering a fake local result list — there is no customer-facing catalog
   full-text-search endpoint in `api.ts`, so this is honestly routed to the
   real conversational/category-matching path instead of invented locally.
4. **Smart Service Assistant card** — one compact CTA, single `sparkles`
   icon, one-sentence purpose line, "Start with SmartBot" affordance (the
   whole card is the tap target, per the brief).
5. **Active booking / empty state** — real data from
   `fieldOpsJobsApi.list()`, matched against `isActive()` (existing helper,
   unchanged). Shows a compact brand banner when a real active job exists;
   otherwise a small, non-dominant neutral row ("No active jobs right now")
   — never a large empty-state banner competing with real content.
6. **Popular services** — 7 compact single-icon tiles (AC Repair, Plumbing,
   Electrical, Cleaning, Appliances, Pest Control, More), 3-per-row grid, no
   badges, no emoji. Tapping a named tile hands its label to SmartBot the
   same way search does; "More" opens SmartBot with no context (full
   category list).
7. **Recent bookings** — real `bookingsApi.list()` data (unchanged data
   source from the prior Home), reusing the existing `BookingCard`
   component; honest empty state pointing at SmartBot when there are none.
8. **Trust row** — 4 short, honestly-scoped claims (Verified pros /
   Transparent pricing / Pay on-site / Customer support). "24/7" was
   deliberately NOT claimed — no evidence of round-the-clock support
   coverage was found elsewhere in the app or backend during this pass.

## Bottom navigation

Exactly 5 tabs: **Home / Bookings / SmartBot / Notifications / Profile**.
"SmartBot" replaces the prior "AI Chat" label on the same
`DeepSeekChatScreen` component (no new screen). "Alerts" is the short label
used for the Notifications tab icon (kept ≤10 chars, single line, verified
by a real render test in `TabNavigator.test.tsx`). The prior standalone
"Chat" tab (human/provider support) is not deleted — see
`category-smartbot-handoff.md`'s sibling note and
`customer-home-implementation-report.md` for the fold-into-Profile decision
and rationale.
