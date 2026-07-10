# CUSTOMER-FRONTEND-01 — Forbidden Label Scan

## Scan performed
```
grep -rniE "wallet|withdraw|escrow|payout|bargain|admin min|admin max|provider internal range|internal score|usage credit deduction|commission|security deposit|platform pay now|online payment required" frontend/customer-app/app frontend/customer-app/components frontend/customer-app/lib
```
Result: **zero matches** (confirmed 2026-07-09 in this session).

Individually checked terms from the exact spec list, all absent from
`frontend/customer-app` source:
Cash Wallet, Wallet Balance, Withdraw, Withdrawable Balance, Tenant Payout,
Provider Earnings Wallet, Escrow, Platform Collected Service Payment,
Provider Cash Balance, Credit Wallet Health, Platform Pay Now, Online Payment
Required, Manual Bargain Setup, Bargain Rule Builder, Admin Min, Admin Max,
Provider Internal Range, Internal Score, Usage Credit Deduction, Commission,
Security Deposit.

## Allowed labels present (confirmed intentional, matches spec whitelist)
Low, Mid, High, Recommended (badge text), Selected price+amount (rendered as
"Selected price: {tier} — ₹{amount}"), "Pay provider directly after service.",
"Customer Pays Provider Directly", "Booking Confirmed", "Provider Assigned"
(referenced in tracking labels), "Track Booking", "Rate Your Experience".

## Enforcement
A Python test (`tests/test_customer_frontend_01_scaffold.py::
test_no_forbidden_finance_labels_in_any_source_file`) walks every `.ts`/`.tsx`/
`.css` file under `frontend/customer-app` (excluding `node_modules`/`.next`) and
asserts none of the forbidden strings are present, so future edits that
reintroduce a forbidden label will fail this test.
