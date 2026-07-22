# Guided SmartBot Design Contract (UX-07 Pass 3d)

## Scope actually delivered this pass

This pass's SmartBot work is the **category-handoff** mechanism (see
`category-smartbot-handoff.md`) plus a compact category-context header and
honest fallback notice inside the existing booking-flow modal. It is
**presentation/flow-structure only around the existing real calls** — no
booking API call, `ServiceBooking`→`ServiceJob` contract field, bargain/
standard-price logic, or idempotent-confirm behavior was touched (verified:
`homeServiceDraftApi.*`, `bookingConfirmApi.confirmHomeServiceBooking`, and
`chatBookingReducer` are byte-for-byte unchanged except for the new
`handoffConsumed`/`categoryMatchLabel` local state added around them).

## What was NOT restructured this pass (honestly deferred)

The brief's fuller Part B ask — a genuinely new "one question + progress
indicator + expandable answers-so-far summary + de-emphasized free-text"
visual restructuring of the *entire* booking-flow modal — was **not**
built this pass. The existing modal already renders one step's UI at a
time (it's a step-conditional render, not a scrolling history), so the
core "no wall of prior Q&A" requirement was already structurally true
before this pass; what's still missing against the fuller brief is:

- A literal "Step X of Y" / segmented progress indicator.
- A compact expandable "answers so far" summary component (today, prior
  answers are implicit in `booking` state and not shown back to the
  customer at all — arguably honest-by-omission, but not the explicit
  summary the brief asked for).
- Auto-advance-after-single-choice vs explicit-Continue-for-multi-select
  behavior differentiation (today every step already advances immediately
  on selection; there is no multi-select step in the current flow to
  differentiate against).

These are logged in `deferred-pass-4-work.md` rather than claimed done.

## Why category-handoff was prioritized over the full visual restructure

Given the pass's time budget, landing a real, tested, functioning handoff
(the concrete "don't ask twice" bug named in the brief) was judged higher
value than a larger cosmetic restructuring of a modal that was already
step-conditional. This is the honest trade-off this report is naming, not
a claim that Part B is fully done.

## Language switching — verified real, not just themed

`language` is a `useState` local to `DeepSeekChatScreen`, entirely separate
from `booking` (a `useReducer` also local to the same component). Switching
`language` re-renders with the new `ChatLanguageOption` but never
dispatches a `RESET` (or any) action against `chatBookingReducer` — so
category/offering/draft/price state gathered so far survives a language
switch by construction, not by luck. This was verified with a real test
(`DeepSeekChatScreen.handoff.test.tsx`'s third case), not just asserted from
reading the code.
