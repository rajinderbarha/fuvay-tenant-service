# Bargain Optionality Decision — UX-06 Round 5

**Finding**: for the `home_service_booking` pipeline, provider-matching +
price-tier selection (`match-and-price` → `confirm-price-choice`) is a
**mandatory** infrastructure step before `finalize()` will ever accept a
draft — there is no code path to book at the plain catalog-default price
without it. Customer-initiated haggling/counter-offers are optional (not
required by any code path), but tier selection itself is not.

**Decision**: Workstream 2's "normal-price booking path" (skip bargain
entirely, book at the plain server price) **does not exist as a real,
callable backend path for this pipeline** — implementing a frontend "Continue
with this price" button that calls the wrong/nonexistent shortcut would
either (a) silently fail the same way Rounds 3/4 did, or (b) require
inventing a client-side bypass, which is explicitly forbidden. Instead:

1. `DeepSeekChatScreen.tsx` was corrected to call the REAL, complete sequence
   (`match-and-price` → `confirm-price-choice` with tier="mid" as the
   customer's continue-at-standard-tier action → the correct
   `/{draft_id}/confirm` endpoint) — see normal-price-booking-path.md for the
   precise wording used ("Continue with this price" maps to selecting the
   `mid` tier, which is the real backend's own middle price option, not a
   fabricated one).
2. No synthetic bargain session or fake accepted offer is created — the
   `mid` tier value comes directly from the real `match-and-price` response.
3. Because no `BargainRule` exists for `ac_repair` (see
   bargain-contract-audit.md / bargain-configuration-safety.md),
   `match-and-price` still fails with a real `PRICE_OPTIONS_UNAVAILABLE`
   error in this environment — this is now the SOLE remaining blocker (the
   wrong-endpoint bug is fixed), precisely diagnosed, not worked around.
