# CUSTOMER-FRONTEND-02 — Mock Data Scan

Command run:
```
grep -rniE "mockServices|mockBookings|mockProviders|mockPriceOptions|mockTracking|demoBooking|fakeProvider" frontend/customer-app/app frontend/customer-app/lib frontend/customer-app/components
```
Result: **zero matches**.

Additional manual checks:
- Price tiers (Low/Mid/High) are rendered from `matchResult?.price_options || matchResult?.prices || {}` returned by the real `match-and-price` API call — the tier *labels* ("Low"/"Mid"/"High") and static blurb copy are hardcoded UI strings (expected/required — these are the fixed tier names the product always uses), but the **numeric ₹ values** are read from the live API response object, not hardcoded. Confirmed at `PriceStep` in `app/customer/home-services/book/page.tsx`.
- No hardcoded booking IDs found (grepped for UUID-looking string literals in `.tsx`/`.ts` — only the test-id used in this session's own curl commands, which was not committed to any file).
- No fake `request_id` generation found — `request_id` is only ever read from `CustomerApiError.requestId`, sourced from real API error bodies, never synthesized client-side.

## Verdict: PASS. No mock/demo/fake runtime data anywhere in the customer frontend.
