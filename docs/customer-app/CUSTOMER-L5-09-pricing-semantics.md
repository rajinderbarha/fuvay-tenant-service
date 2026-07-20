# CUSTOMER-L5-09 — Pricing Semantics

## Low, Mid, High — Exact Mathematical Meaning

Source: `compute_symmetric_customer_price_tiers`
(`app/engines/admin_catalog/bargain_engine.py:208-260+`), the single formula
this platform uses across its admin console, tenant setup wizard, and now
this customer flow (per the function's own docstring, "the single formula
already certified across the admin pricing console, tenant setup wizard,
and customer price preview").

```
Low  = BargainRule.customer_min_price × (1 + platform_fee_percent / 100) + platform_fee_fixed_amount
High = BargainRule.customer_max_price × (1 + platform_fee_percent / 100) + platform_fee_fixed_amount
Mid  = round_to_nearest(10, (Low + High) / 2)
```

- **Backend source**: `BargainRule` (a per-tenant, per-`master_service_id` — optionally further scoped by `service_type_id`/`brand_id` via the linked `ServicePricingRule` — configuration row), resolved for the already-matched provider from CUSTOMER-L5-08.
- **Mathematical meaning**: `customer_min_price`/`customer_max_price` are the *provider's own* configured price range for this service; `Low`/`High` are that range with the platform fee applied to **both** ends (not just the low end — an explicit bug-fix documented in the backend's own code comments, "HS6 fix"). `Mid` is a real, backend-computed rounded midpoint — this client never recomputes it.
- **Tax included?** No tax field exists anywhere in this response — tax status is not specified by the backend for this flow (see Tax section below).
- **Parts included?** Not specified by any structured field — see Included/Excluded section below for how this sprint handles the absence of itemized components honestly.
- **Inspection included?** Not applicable — this vertical's real `MasterService.pricing_model` values observed in this flow are not `INSPECTION_FIRST`/`QUOTE_REQUIRED` (see Pricing Models section); if a future service uses those models, this sprint's screen still renders whatever `price_options` the backend returns (a range), since the backend does not gate `match-and-price` on `pricing_model` at all.
- **Does provider selection affect it?** Yes, entirely — `Low`/`Mid`/`High` are 100% derived from the specific matched provider's own `BargainRule`. A different matched provider would produce a different range.
- **Does SLA affect it?** No — confirmed, `compute_price_tiers` takes no SLA-related input at all.
- **Does quantity affect it?** No — confirmed, no quantity/unit field exists anywhere in this vertical's real data model (see baseline-verification.md #9).
- **Customer-facing labels used by this sprint**: "Lower estimate" / "Expected estimate" / "Upper estimate" — chosen because the backend provides no `recommended`/`expected` flag (see Recommended Estimate Boundary below) and because "Low/Mid/High" (the internal field names) read as raw technical jargon rather than customer-safe copy.
- **Legal/explanatory text**: this sprint states plainly, using real backend facts only, that the final amount is paid directly to the provider (`payment_mode = "customer_pays_provider_directly"`) and may change based on the provider's own final assessment — it does not invent additional disclaimers about inspection/parts/scope changes the backend has not itself indicated apply to this service.

## Mid Is Not Automatically "Recommended"

Per §32's explicit guardrail, this sprint does **not** treat `mid_price` as
an authoritative "recommended" flag — because no such flag exists in the
real response. It is labeled "Expected estimate" purely as a neutral,
literal description of its real mathematical meaning (the rounded
midpoint of the real range), not as an implied product endorsement.

## Pricing Models — Real vs. Aspirational

`MasterService.pricing_model` (real column, values include at minimum
`"fixed"`, `"visit_fee_plus_quote"`, per `_compute_price_snapshot`'s own
handling — the exact full enumerated set was not exhaustively catalogued
this sprint since `match-and-price` does not gate on this field at all).
**Crucially, `match-and-price`/`compute_price_tiers` never reads
`pricing_model`** — it always returns a `low_price`/`mid_price`/`high_price`
trio once a valid `BargainRule` exists, regardless of what pricing model the
offering is nominally configured with. This is a real, disclosed
architectural fact: **this sprint's real flow only ever produces a RANGE
presentation** (Low/Mid/High) — the spec's aspirational
`FIXED`/`PER_UNIT`/`INSPECTION_FIRST`/`QUOTE_REQUIRED` display variants
described in §14/§16-19 do not correspond to any real, reachable state in
`match-and-price`'s response today. This sprint implements the real RANGE
case fully and honestly, and documents (rather than fabricates) the other
model variants as not reachable through this endpoint — see known-gaps.md.

If `low_price === high_price` (a real, possible degenerate case when
`customer_min_price === customer_max_price`), this sprint's UI collapses to
a single-amount presentation rather than showing a redundant zero-width
range — a real rendering decision based on real returned numbers, not a
separate fabricated "FIXED" pricing model.

## Included and Excluded

No structured `included_items`/`excluded_items`/`components` array exists
in the real response (contract-matrix.md). This sprint does not fabricate
a plausible-looking itemized breakdown. The only real, structured fact
available is `payment_mode = "customer_pays_provider_directly"` — this
sprint surfaces exactly that fact, worded as a real, backend-confirmed
statement ("You pay the provider directly for this service"), and does
not add invented labour/parts/consumables/visit-charge line items the
backend has not itself provided. `known-gaps.md` documents this as a real
product gap (no itemized cost breakdown exists anywhere in this backend
today) rather than working around it with fabricated content.

## Estimate vs. Final Price

This sprint's copy distinguishes "estimated price" (what is shown) from
"final amount" using only backend-supported facts: the estimate is a
range (Low/Mid/High) already reflecting the specific matched provider's
own configured pricing, and the actual amount charged is whatever the
customer selects via `confirm-price-choice` (CUSTOMER-L5-10) followed by
direct payment to the provider (`payment_mode`). This sprint does not
invent reasons ("inspection may reveal additional issues," "parts not
included") the backend has not itself indicated apply — see Tax/Included
sections above for why those specific claims cannot be made honestly here.

## Pricing Validity

No price-specific expiry exists (contract-matrix.md) — only the generic,
whole-draft `expires_at` (24 hours from draft creation,
`DRAFT_EXPIRY_HOURS = 24`). This sprint therefore does not display a
price-specific "valid until" countdown (there is no real value to show);
instead, it always re-derives a fresh estimate on screen entry (mirroring
`match-and-price`'s real overwrite-on-recall semantics) and offers an
explicit "Refresh estimate" action that re-runs the same real call.

## Tax

No tax field exists anywhere in this flow's real responses
(`ServicePricingRule.tax_percent` exists in the schema but is confirmed
never read by `compute_price_tiers`/`match_provider_and_price`). This
sprint's UI states "Tax status not specified for this estimate" rather
than guessing "tax included" or "tax excluded" — an honest gap disclosure,
not a fabricated claim in either direction.

## Bargain Eligibility — Why This Sprint Shows No Claim

Per baseline-verification.md finding #24: `BargainRule.bargain_enabled`
exists in the database but is never read by `match-and-price`, and no
`bargain_allowed`-equivalent field is ever returned to the customer. This
sprint therefore does **not** display "You can negotiate this estimate" or
"Fixed price, bargaining unavailable" — both would be inferred, unverified
claims the backend does not actually make. The presence of a real
Low/Mid/High range is not proof that `bargain_enabled = true`, since that
flag is confirmed dead code in this flow. This is a deliberate,
documented omission (see known-gaps.md), consistent with this project's
established pattern of never fabricating a plausible-looking but
unverified UI signal.
