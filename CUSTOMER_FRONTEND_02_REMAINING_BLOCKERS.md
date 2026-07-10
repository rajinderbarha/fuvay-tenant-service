# CUSTOMER-FRONTEND-02 — Remaining Blockers / Known Gaps

1. **No real browser click-through performed** — still no Playwright/Selenium/Puppeteer/browser DOM tool available in this environment; all verification is curl.exe HTTP-status checks plus static source-code inspection. This alone forces the honest verdict away from full READY certification, per the sprint's own stated rule.

2. **Provider matching still returns `HOME_BOOKING_NO_PROVIDER_AVAILABLE` for the only seeded serviceable zipcode (141001/141002, Ludhiana)** — unchanged from Sprint 01. Confirmed live again this session with the same real 422 + request_id. This is backend catalog/provider-enablement seed data, explicitly out of this sprint's strict scope ("do not work on... backend engine redesign"). As a direct consequence: Low/Mid/High pricing, booking creation, tracking of a real booking, and review submission against a real completed booking were **not observed as live successes** this session either — only verified as correctly-implemented code paths.

3. **No completed booking exists** in this dev DB for the seeded customer (`GET /v1/customer/bookings` -> `{"items":[]}`), so review submission remains untestable live, same root cause as #2.

4. **No middleware-level auth route guard** — `/customer/*` page shells return HTTP 200 even without a token; the client-side data fetch then 401s and redirects to `/login`. Not a security hole (backend enforces auth on every real data call, confirmed by source read of `home_service_assignment/customer_router.py`), but a minor UX flash. Not fixed this sprint — adding Next.js middleware was judged outside the "bug fix" scope without breaking the existing SSR/CSR split, and is better done as its own reviewed change.

5. **Cross-customer-access denial verified in code only, not with two live accounts** — only one seeded customer user exists in this dev DB. The `customer_id` re-derivation-from-JWT + ownership check pattern was confirmed present in `home_service_assignment/customer_router.py` (lines 54/89/93/138/142/206/211/226/239/246/263/266/275), not exercised with a second real account.

6. **Raw backend status enum shown to customer** on the booking-detail/tracking page (e.g. `pending_assignment`) instead of a humanized label. Cosmetic only, not a forbidden term, not fixed this session (would require guessing at the full enum surface without a live example to validate against).

7. **No auto-refresh/poll on the tracking page** — it re-fetches on mount/navigation only, no interval or websocket. Acceptable per spec ("real-time push isn't required unless already built") but worth tracking as a future improvement.

8. **customer-app has its own local `ErrorBanner.tsx`** rather than sharing a cross-portal error-state component with admin/tenant portals — a documented duplication, not a defect, out of this sprint's scope to consolidate.

9. **`cancel-after-confirmation` remains unwired** (unchanged from Sprint 01) — `cancelCustomerBooking()` still throws a clear "not wired" error rather than faking success; no backend route exists for it.

10. **Dedicated "service questions" endpoint still does not exist** backend-side (unchanged from Sprint 01) — the Details step uses flow-config + service-options/issue-types as a real substitute, documented in the API Contract report.

## Genuine fix made this sprint
- `app/customer/home-services/book/page.tsx`: the "Confirm Booking" button in `ReviewStep` was disabled only on `loading`; it is now also disabled when `!priceTier` or no provider name is present, closing a defensive gap (the normal step-flow already guaranteed both were set, but the button itself didn't enforce it).

## What would need to happen next (out of this sprint's scope)
Fix backend provider-enablement/bookability seed data for at least one offering+zipcode combination so a real end-to-end booking (match -> price -> confirm -> track -> complete -> review) can be observed live. Everything upstream of that point (auth, catalog, draft creation, serviceability) is proven live and working.
