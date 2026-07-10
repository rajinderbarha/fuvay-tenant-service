# Tenant Home Services Setup — Test Results

## Run Date: 2026-07-09

### test_tenant_home_services_setup_wizard.py

**Result: 69 passed / 0 failed**

| Category | Tests | Result |
|----------|-------|--------|
| Page existence + client directive | 3 | ✅ |
| Service catalog (title, subtitle, APIs) | 5 | ✅ |
| Service cards (Set Up / Manage / Continue) | 4 | ✅ |
| Wizard modal | 2 | ✅ |
| Overview step | 3 | ✅ |
| Info cards (pricing model, brands, types) | 3 | ✅ |
| Types step | 3 | ✅ |
| Type selection state | 2 | ✅ |
| Pricing step | 2 | ✅ |
| Admin floor/ceiling validation | 2 | ✅ |
| Customer Price Preview (Low/Mid/High) | 3 | ✅ |
| Platform fee | 2 | ✅ |
| Brand step | 2 | ✅ |
| Same for all / Override some | 3 | ✅ |
| Brand override component + validation | 2 | ✅ |
| Review step + matrix | 3 | ✅ |
| Save Draft | 2 | ✅ |
| Publish blocked without area | 2 | ✅ |
| Publish action | 1 | ✅ |
| No manual bargain wording | 1 | ✅ |
| No forbidden labels | 1 | ✅ |
| Safe helpers + NaN guard | 2 | ✅ |
| Error: request_id + retry + copy | 3 | ✅ |
| Scope guard | 3 | ✅ |
| API surface (setTypePricing, pricePreview, saveDraft, publish) | 4 | ✅ |
| Wizard architecture (steps, left panel, labels, completed) | 4 | ✅ |
| No free-text service creation | 1 | ✅ |
| Customer / Provider labels | 2 | ✅ |
| Direct on-site payment copy | 1 | ✅ |

## TypeScript

```
cd frontend/tenant-portal && npx tsc --noEmit
Exit code: 0 — no errors
```
