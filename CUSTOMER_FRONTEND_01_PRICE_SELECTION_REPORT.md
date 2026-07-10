# CUSTOMER-FRONTEND-01 — Price Selection Report

Implemented in the `PriceStep` component inside
`frontend/customer-app/app/customer/home-services/book/page.tsx`.

- Values (`low`/`mid`/`high`) are read directly from the `match-and-price` response
  (`matchResult.price_options` or `matchResult.prices`, whichever key the live
  backend returns — both are checked defensively since exact response key naming
  was not observed with a real 200 in this DB's data, see Live API Verification
  Report) and rendered as-is; no arithmetic is performed client-side.
- Copy matches spec exactly: Low "Budget-friendly option", Mid "Recommended fair
  price" (with a "Recommended" badge), High "Higher acceptance priority".
- Selection is single-select client state (`priceTier`); the Continue button is
  disabled until a tier is chosen (`disabled={loading || !priceTier}`).
- "Pay provider directly after service." note is rendered under the cards.
- Confirming a tier calls `confirmPriceChoice(draftId, priceTier)` which POSTs only
  `{price_tier: "low"|"mid"|"high"}` — never a raw amount — matching the backend
  contract described in `home_service_booking/customer_router.py`'s own docstring
  ("Customer submits only a tier name... never a raw amount and never a provider").
- Forbidden terms (Wallet, Escrow, Payout, Platform Payment, Pay Platform Now,
  Provider Earnings) do not appear anywhere in this component or its copy — see
  CUSTOMER_FRONTEND_01_FORBIDDEN_LABEL_SCAN.md.

## Gap
No live 200 response from `/match-and-price` was obtained in this dev DB (every
provider/zipcode/brand combination available seeded no matching provider), so the
exact response key for price options (`price_options` vs `prices` vs something
else) was not confirmed against a real payload — the frontend defensively checks
both common names. This must be re-verified against a live 200 before declaring
this step fully certified.
