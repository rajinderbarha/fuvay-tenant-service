# HS6 — Auto Price Options Report

## Real bug found and fixed
`compute_price_tiers()` (`matching_engine.py`) delegated entirely to
`evaluate_customer_bargain()` from `bargain_engine.py`. That function's
`allowed_offer_max` is defined as the **raw `customer_max_price`, with
no platform fee applied** — so `high_price` in every provider-matching
price-options response equaled the pre-fee provider max, directly
violating this ticket's explicit hard gates:
- "High must include platform fee." — **was failing.**
- "High must not equal pre-fee provider max." — **was failing** (it
  always equaled it, exactly).

This is the same asymmetric-formula bug already found and fixed on the
**admin preview endpoint** in an earlier sprint this session — but
`compute_price_tiers()` in `matching_engine.py` is a *separate function
of the same name in a different module* that was never touched by that
earlier fix.

## Fix
`compute_price_tiers()` now delegates to
`compute_symmetric_customer_price_tiers()` (the single, already-
certified formula used by the admin pricing console, the tenant setup
wizard, and the customer price preview throughout this session) for the
final Low/Mid/High numbers, while still calling
`evaluate_customer_bargain()` first purely to preserve its admin/
customer-range configuration validation (still raises
`BargainValidationError` on an invalid setup, unchanged).

## Live-verified against the ticket's own example
```python
compute_price_tiers(admin_min=500, admin_max=900, customer_min=700, customer_max=850, fee=10)
→ low_price: 770.0, high_price: 935.0, payment_mode: "customer_pays_provider_directly"
```
Exactly matches the ticket's worked example (Low ₹770, High ₹935).

## Hard gates — all now pass
1. Low includes platform fee ✅ (`770 != 700`)
2. High includes platform fee ✅ (`935 != 850`, confirmed via new test
   `test_high_price_includes_platform_fee_not_raw_max`)
3. Mid is between Low and High ✅ (unchanged property, still holds)
4. High does not equal pre-fee provider max ✅ (explicit new test)
5. Low does not equal pre-fee provider min ✅ (explicit new test)

## Verdict
Auto Low/Mid/High: **critical bug found and fixed**, live-verified
against the ticket's own numeric example, all 5 hard gates now pass
with dedicated regression tests.
