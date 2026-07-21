# Round 6 — Bargain Optionality Proof (definitive)

## The precise question

*"Does the confirm/price-choice flow require a bargain/tier result, or can it
proceed with the plain server-returned price when no BargainRule exists?"*

## Answer: NO fallback exists. Confirmed by direct code reading.

`match_provider_and_price()` (`app/engines/home_service_booking/service.py:532-660`)
unconditionally requires a `BargainRule` row for the requested
`master_service_id`:

```python
bargain_candidates = (await self.db.execute(
    select(BargainRule, ServicePricingRule)
    .join(ServicePricingRule, ServicePricingRule.id == BargainRule.pricing_rule_id, isouter=True)
    .where(
        BargainRule.master_service_id == master_service_id,
        BargainRule.status == "active", BargainRule.deleted_at.is_(None),
    )
)).all()
...
bargain_rule = eligible_candidates[0][0] if eligible_candidates else None
if not bargain_rule or bargain_rule.customer_min_price is None or bargain_rule.customer_max_price is None:
    raise ServiceOSException(
        "PRICE_OPTIONS_UNAVAILABLE",
        "Selected provider does not have a customer price range configured yet.",
        status_code=422,
    )
```

There is **no `if`/`else` branch, no feature-flag check, no fallback to plain
`ServicePricingRule`-only pricing** anywhere in this function. This is a hard,
unconditional requirement in the current code — not a matter of environment
configuration that could be worked around client-side.

## An important nuance found this round: a real, unreconciled feature-flag mismatch

`app/engines/admin_catalog/auto_price_options_router.py`'s own docstring
states: *"Replaces manual Bargain Rule setup for Home Services... the backend
automatically derives Low/Mid/High customer price options (no manual 'bargain
rule' authoring required)"* and `app/core/feature_flags.py` defines
`auto_price_options_enabled` defaulting to `True` and
`manual_bargain_rules_enabled` defaulting to `False` — i.e., the platform's
own stated default behavior is that manual `BargainRule` authoring should NOT
be required. **`match_provider_and_price()` never checks either flag** — it
unconditionally requires the manual `BargainRule` row regardless of flag
state. This is either a real, unfixed backend gap (the auto-pricing rollout
never got wired into the actual booking/matching code path) or an
intentional two-stage design not yet complete. Either way, it is backend
code — flagged here for the backend team, not modified (UX-06 makes zero
backend changes).

## Tier selection vs. bargain/negotiation — the real distinction

Confirmed: "tier selection" (customer picks one of 3 server-computed
low/mid/high options) is mandatory infrastructure requiring a `BargainRule`.
Genuine customer-initiated haggling/counter-offer submission is a DIFFERENT,
separate concept that has **no code path anywhere** in this engine — the
customer never submits a custom amount, only picks among 3 backend-computed
values. So "bargain" in the sense of negotiation is not just optional, it
doesn't exist as a feature at all in this pipeline; but "bargain" in the
sense of "the BargainRule-driven tier-selection step" is mandatory and not
skippable.

## This is Outcome B for `ac_repair` specifically — with a critical Item-4 discovery

**Outcome B applies to `ac_repair`**: no legitimate way exists to book it
without a `BargainRule`, and creating a new platform-wide one was correctly
declined (bargain-configuration-safety.md, Round 5 — still valid, re-checked
this round, nothing changed there).

**However, a real, pre-existing, already-configured combination exists**:
a live `bargain_rules` row already exists for `master_service_id =
13f6cf5e-5d17-4790-b406-6561675a5d38` (`ac_installation`,
`customer_min_price = customer_max_price = 150.00`, `status: active`),
confirmed via a read-only `SELECT` against the real database:

```sql
SELECT br.master_service_id, ms.slug, br.customer_min_price, br.customer_max_price, br.status
FROM bargain_rules br LEFT JOIN master_services ms ON ms.id = br.master_service_id
WHERE br.deleted_at IS NULL;
-- 13f6cf5e-5d17-4790-b406-6561675a5d38 | ac_installation | 150.00 | 150.00 | active
```

This is the exact legitimate path the Round 6 brief anticipated ("check if
any other existing master_service already has a BargainRule row... THAT
would be a legitimate way to prove the pipeline without creating new
policy"). Used to run the complete real booking proof — see
canonical-booking-live-evidence.md.

## One honest caveat

`ac_installation` is a real `MasterService` row (used by the booking
pipeline directly, matched by slug) but is **not currently listed in the
customer-facing catalog** (`GET /v1/customer/categories/home_services/offerings`
returns only `ac_repair`) — it exists in `MasterService` but apparently not
as a customer-visible `MasterOffering`. This means a real end-user browsing
the actual app's category/offering picker still cannot reach `ac_installation`
today; the draft was created this round by passing its slug directly (which
`start_booking_draft` accepts since it resolves against `MasterService`
directly, independent of the customer catalog's `MasterOffering` list — a
real, pre-existing decoupling between these two catalog surfaces, not
something this round created). Making `ac_installation` customer-visible
would require a backend catalog data change, out of scope for UX-06.
