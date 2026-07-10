# E2E-11 Mock Data Scan

## Scan Method
Searched for: `hardcoded`, `mock`, `fake`, `dummy`, inline array literals in JSX data positions.

## Files Scanned
- All finance pages
- Notifications page
- Settings page

## Findings
**No mock data found.** All pages:
- Use `useApi()` hook with real API function calls
- Show `Skeleton` loaders while loading
- Show honest empty states when API returns no data
- Show error banners with request IDs on API failures

## Hardcoded UI Structure (Not Data)
- `security-deposit/page.tsx` has `required_amount ?? 5000` and `currency ?? "INR"` as fallback defaults for display when API returns null — acceptable defensive defaults, not mock data
- `package/page.tsx` has `staff_limit ?? 5` and `service_area_limit ?? 5` as display fallbacks — acceptable

## Status: PASS
