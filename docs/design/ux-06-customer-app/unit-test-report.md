# Unit Test Report — UX-06 Round 4

Fresh WSL run, `npx jest --runInBand`: **23/23 passing** (up from 19 at Round
3 end). New this round: `bookingContract.test.ts` (4 tests) — proves
`homeServiceDraftApi.start()` sends only real fields (no price/tenant
override), `bookingConfirmApi.confirmHomeServiceBooking()` sends a real
`Idempotency-Key` header and never a client price, a duplicate-submission
retry reuses the same idempotency key, and `serviceabilityCheck`/`priceEstimate`
are body-free POSTs (nothing client-supplied to override server authority).

Suite composition: `api.test.ts` (7), `chatBookingState.test.ts` (8),
`AuthContext.test.tsx` (4), `bookingContract.test.ts` (4).
