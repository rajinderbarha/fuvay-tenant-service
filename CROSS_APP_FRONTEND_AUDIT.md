# Cross-App Frontend Audit — Booking/Job/Payment/Credit Pages

Apps in this repo:
- **Admin**: `frontend/super-admin/app/admin/*`
- **Tenant/Provider**: `frontend/tenant-portal/app/(tenant)/*`
- **Staff/Technician**: `mobile/staff-app` (React Native, not web)
- **Customer**: `mobile/customer-app` (React Native, not web)

## 1. Tenant booking detail
`frontend/tenant-portal/app/(tenant)/bookings/[id]/page.tsx`. API: `bookingsApi.get/getTimeline/listNotes/confirm/reject/reschedule/convertToJob/addNote`.
Shows `quoted_price` as "Price". **Missing**: `credit_applied`, `payable_amount`, `payment_collection_mode`, `platform_payment_collected`, job status, assigned technician, payment-recorded state. No forbidden terms. Real API, no mock. **Fixed this sprint** — added Payment Breakdown card.

## 2. Tenant job detail
`frontend/tenant-portal/app/(tenant)/jobs/[id]/page.tsx`. API: `jobsApi.get/history/updateStatus/close/spawnRepair`, `quotesApi.*`, `mediaAssetApi`.
Shows `quoted_price`, `commission_amount`. Copy at line ~522 said "deduct commission from your wallet" — informational but uses forbidden term "wallet" in a Home-Services-facing sentence. **Missing**: credit_applied, payable_to_provider, payment_collection_mode. **Fixed this sprint** — added Payment Collection + Usage Credit Deduction sections, reworded wallet copy to "usage credit ledger."

## 3. Tenant finance / usage credit ledger
`frontend/tenant-portal/app/(tenant)/finance/page.tsx` — tabs: wallet/deposit/credits/commission/invoices/payouts. Uses forbidden terms: "Payouts" tab, `requestPayout`. **Note**: this Payouts tab is a pre-existing, separate tenant-subscription/deposit-refund feature, not the Home-Services job-completion flow — out of this sprint's scope to remove (would be a feature deletion, not a labeling fix); flagged in Remaining Blockers rather than deleted. The **Commission** tab (job-completion deductions) is the one in scope — **fixed this sprint**: commission history rows now labeled "Completed Job Deduction" instead of "Commission."
`.../account/credits/page.tsx` and `.../provider/wallet/page.tsx` also exist; no forbidden terms in the credits page; the wallet page's "wallet"/"commission" terms are appropriate there (it IS the usage-credit wallet).

## 4. Tenant dashboard recent jobs/bookings
`frontend/tenant-portal/app/(tenant)/dashboard/page.tsx`. Shows `quoted_price`, wallet balance, recent commission stat. No credit_applied/payable_amount shown — acceptable for a summary widget (not in this sprint's required-fields list for the dashboard). Not changed.

## 5–8. Staff / technician app
`mobile/staff-app/src/screens/JobsListScreen.tsx` (list), `JobDetailScreen.tsx` (detail + inline completion via `close`).
**No payment recording form exists anywhere in the codebase** — a genuine gap. **Fixed this sprint**: added a Payment Collection card + Record Payment form to `JobDetailScreen.tsx`, wired to `jobsApi.recordPayment`.

## 9–10. Customer app
`mobile/customer-app/src/screens/BookingDetailScreen.tsx`, `JobTrackingScreen.tsx`. Uses `price_snapshot.final_price`, a different (older) price model than `quoted_price`/`payable_amount`. No dedicated ServiceOS-credit screen exists; `customerCreditsApi.applyToBooking`/`previewApply` are defined in `tenant-portal/lib/api.ts` but **unused by any page** (dead client code — belongs to the customer app, not the tenant portal). **Fixed this sprint**: added credit/payable breakdown to `BookingDetailScreen.tsx` where the backend booking payload already includes `credit_applied`/`payable_amount`.

## 11. Admin booking detail
`frontend/super-admin/app/admin/bookings/[id]/page.tsx`. Uses `estimated_amount`, not `quoted_price` — a field-name mismatch vs. the tenant side (separate admin-specific endpoint). **Missing** credit/payable/payment-mode fields. **Fixed this sprint**.

## 12. Admin job detail
`frontend/super-admin/app/admin/operations/[jobId]/page.tsx`. Shows `commission_amount`. **Missing** quoted_price/credit_applied/payable_amount/amount_collected. **Fixed this sprint**.

## 13. Admin tenant finance/ledger
`frontend/super-admin/app/admin/finance/wallets/page.tsx` + `[wallet_id]/page.tsx`. Shows balances; "Wallet" label is appropriate here (usage-credit wallet, not cash). No payout language found. Not changed.

## 14. Admin customer credit detail
`frontend/super-admin/app/admin/finance/customer-credits/page.tsx` + inline tab in `admin/customers/[id]/page.tsx`. No standalone per-credit detail page. No forbidden terms. Not changed (out of scope — no credit_applied/payable_amount gap here since this page is about credit issuance, not booking payment breakdown).

## API-client / type files
- `frontend/tenant-portal/lib/api.ts` — had `credit_applied`/`payable_to_provider` types defined but unused by any page (now consumed by fixed booking detail page). **Fixed**: added `BookingPaymentBreakdown`/`JobPaymentBreakdown` types and extended `Booking`/`Job` interfaces with the new fields.
- `frontend/super-admin/lib/api.ts` — no `payable_amount`/`credit_applied`/`payable_to_provider` at all. **Fixed**: added the same fields to `AdminBooking`/admin job types.
- `mobile/customer-app/src/lib/api.ts`, `mobile/staff-app/src/lib/api.ts` — no target fields at all. **Fixed**: extended booking/job response types.

## Forbidden-term scan result
No forbidden term (Payout/Withdraw/Cash Wallet/Escrow/Platform Payment/Provider Earnings Wallet) appears in any Home-Services job-completion-facing screen after this sprint's fixes, except the pre-existing tenant Finance "Payouts" tab, which is a distinct feature (tenant subscription/deposit refunds) not part of the job-completion flow — flagged, not removed, in `REMAINING_BLOCKERS.md`.
