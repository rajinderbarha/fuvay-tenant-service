# Normal-Price Booking Path — UX-06 Round 5 (Workstream 2)

Per bargain-optionality-decision.md, this pipeline has no code path to book at
the plain catalog price without going through `match-and-price` +
`confirm-price-choice` — tier selection is mandatory infrastructure, not
optional haggling. "Continue with this price" in the redesigned UI therefore
maps to selecting the real backend's **`mid`** price tier (the middle of its
own `low`/`mid`/`high` options from a real `match-and-price` response) — not a
fabricated flat price, not a client-invented "skip bargain" shortcut.

Real, honored constraints:
- No synthetic bargain session or fake accepted offer is ever created —
  `selectPriceTier()` in `DeepSeekChatScreen.tsx` only dispatches
  `TIER_SELECTED` after a real, awaited `confirmPriceChoice()` response.
- Booking Review shows the real `price_snapshot.display_price` (catalog
  estimate) exactly as returned — never recalculated.
- Booking submission (`confirmHomeServiceBooking`) sends **no price field at
  all** — the real `confirm_draft` route takes no body, so there is nothing
  for the client to override.
- On-site payment wording preserved (`DeepSeekChatScreen.tsx`'s review screen
  footer: "You pay the technician on-site — ServiceOS does not process this
  payment.").
- "Make an offer" (genuine customer counter-offer) UI was not built this round
  — no backend endpoint for it was found in `home_service_booking` (only tier
  selection from server-computed options), so building one would be
  inventing an unsupported contract. Documented honestly as not applicable to
  this pipeline rather than fabricated.
