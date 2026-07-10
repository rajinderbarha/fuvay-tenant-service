# HS3 — Customer Price Preview Calculation Report

## Formula (unchanged, already correct)
`compute_symmetric_customer_price_tiers` in
`app/engines/admin_catalog/bargain_engine.py` — the single shared
formula used by the admin pricing console, the tenant setup wizard, and
the customer price preview.

## Ticket's exact example — live re-verified this sprint
```python
compute_symmetric_customer_price_tiers(350, 420, platform_fee_percent=10)
→ {low_price: 385.0, mid_price: 420.0, high_price: 462.0, payment_mode: "customer_pays_provider_directly"}
```
- Low ₹385 — **matches ticket exactly**.
- High ₹462 — **matches ticket exactly**.
- Mid: real function returns **₹420**; the ticket's own worked example
  says "Mid = (Low+High)/2 rounded to nearest ₹5 = ₹423.5 → ₹425". This
  is a **known, pre-existing deviation** from the ticket's midpoint-
  rounding description — the real function does not compute mid as a
  post-hoc average-and-round of low/high; it derives mid directly from
  the provider range. Not changed this sprint (see Remaining Blockers —
  changing the formula would affect every already-certified caller of
  this shared function across 3+ sprints, too risky to change without
  an explicit product decision).

## Hard gates — all confirmed
- Low includes platform fee: `385 != 350` (pre-fee provider min) ✅
- High includes platform fee: `462 != 420` (pre-fee provider max) ✅
- Payment mode: `"customer_pays_provider_directly"` — confirmed literal
  string in `bargain_engine.py`, no forbidden terms ("Platform Collected
  Payment", "Escrow", "Provider Payout", "Withdraw") found anywhere in
  that file.

## Preview panel scope
The admin pricing-rules page does not currently have a dedicated
"Preview Customer Price" top action or side panel showing Resolved
Pricing Rule / Admin Allowed Range / Provider Selected Range / Platform
Fee on Min / Platform Fee on Max breakdown as separate labeled fields —
it shows the rule table only. The underlying calculation is correct and
reachable (via the tenant-side wizard's own preview, already certified),
but the ticket's specific **admin-side preview panel UI** was not built
this sprint. Documented in Remaining Blockers.

## Verdict
Calculation: **correct and hard-gate-compliant** (Low/High both include
fee, correct payment mode). Mid's rounding behavior deviates from the
ticket's example by ₹5 (₹420 vs ₹425) — pre-existing, not touched.
Dedicated admin-side preview UI panel: **not built** this sprint.
