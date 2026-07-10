# Tenant Menu Cleanup Report

## Before

Setup group contained:
- Setup Checklist
- Business Profile
- **Service Setup**
- **Service Pricing Setup** ← removed
- **Pricing Setup** ← removed
- **Customer Price Preview** ← removed
- Availability

Coverage group (now removed):
- Service Areas ← moved to Setup
- Service Coverage ← removed from sidebar

## After

### Setup (final)
- Setup Checklist → `/provider/status`
- Business Profile → `/profile`
- Service Areas → `/provider/service-areas`
- Service Setup → `/provider/service-setup`
- Availability → `/provider/availability`

### Finance (unchanged, correct)
- Package & Credits → `/finance/package`
- Usage Credit Ledger → `/finance/usage-credit-ledger`
- Security Deposit → `/finance/security-deposit`

## Files Modified

| File | Change |
|------|--------|
| `components/layout/TenantLayout.tsx` | Removed 3 old Setup items + Coverage group; moved Service Areas into Setup |
| `lib/nav-config.ts` | Removed `provider-pricing` from Setup; added `provider-service-setup`; remapped `pricing` path |
| `app/(tenant)/provider/pricing/page.tsx` | Replaced with deprecated redirect to Service Setup |
| `app/(tenant)/provider/customer-price-preview/page.tsx` | Replaced with deprecated redirect |
| `app/(tenant)/tenant/setup/services/page.tsx` | Replaced with deprecated redirect |
| `app/(tenant)/provider/service-setup/page.tsx` | Added provider price range input + Low/Mid/High preview step |

## Forbidden Labels — Not Present

All confirmed absent: Wallet Balance, Cash Wallet, Withdraw, Withdrawable Balance, Tenant Payout, Provider Earnings Wallet, Escrow, Provider Cash Balance
