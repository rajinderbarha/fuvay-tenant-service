# Bargain Optionality Decision — UX-06 Round 5

## Explicit correction to the Round 5 brief's premise

The Round 5 brief's Workstream 2 assumes bargain/tier-selection is likely
optional and asks the implementer to prove a "normal-price" path exists that
skips it. **The real backend code does not support this premise.** Read
directly (not inferred from the UI): `mark_ready_for_confirmation()`
(`app/engines/home_service_booking/service.py:822-892`) unconditionally
raises `ERR_NO_PROVIDER_AVAILABLE` unless `draft.selected_tenant_id` and
`draft.price_snapshot["price_options"]` are both set (only possible via a
successful `match_provider_and_price()` call) AND
`draft.booking_summary.selected_price_tier` is one of `"low"/"mid"/"high"`
(only possible via `confirm_price_choice()`). There is no `if` branch, feature
flag, or alternate call path anywhere in `finalize()` or
`mark_ready_for_confirmation()` that accepts a draft which skipped these
steps. This was verified twice: once by static code reading, and once live —
supplying every other required field correctly (Round 5 commit 1) still
produces a real `HOME_BOOKING_NO_PROVIDER_AVAILABLE`/
`PRICE_OPTIONS_UNAVAILABLE` rejection specifically at the matching/tier step,
with nothing else blocking.

**Reconciliation**: rather than force an "optional, skippable" UI the backend
doesn't actually support (which would either silently fail or require
inventing a client-side bypass — both forbidden), the frontend and this
round's own tests (`chatBookingState.test.ts`'s Round 5 additions) were built
to match the REAL contract: tier selection is mandatory infrastructure for
every `home_service_booking` booking, not optional per-customer haggling.
"Optional" only describes whether the customer negotiates a custom
counter-offer (no code path for that exists either — the customer only
chooses among 3 server-computed tiers) — it does NOT mean the customer can
skip straight from the catalog price-estimate to booking. This is a genuine,
verified correction to the original brief's assumption, not a hedge.

## Original finding (Workstream 1 audit)

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
