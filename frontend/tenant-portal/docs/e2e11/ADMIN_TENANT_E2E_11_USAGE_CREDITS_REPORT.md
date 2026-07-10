# E2E-11 Usage Credits Page Report

## Page: `/finance/package`
File: `app/(tenant)/finance/package/page.tsx`

## API
- `usageCreditsApi.getBalance()` → real endpoint (HS9/HS9B)
- `tenantSetupApi.getPackage()` → package details

## Labels Verified
- Heading: "Package & Credits" ✅
- Card title: "Usage Credit Balance" ✅
- Balance description: "credits available" ✅
- Low credit message: "Low Usage Credits" ✅
- Job deduction text: "Each completed job deducts usage credits from your balance." ✅

## Forbidden Labels: NONE FOUND
No "Wallet Balance", "Cash Wallet", "Recharge", or "Payout" in rendered JSX.

## Status: PASS
