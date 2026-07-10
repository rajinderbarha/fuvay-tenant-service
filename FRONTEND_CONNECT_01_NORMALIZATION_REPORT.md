# FRONTEND-CONNECT-01 — Normalization Report

## tenant-portal
`lib/status-format.ts` already had `safeNum, safeText, safeCurrency, safePercent, safeDate, safeArray, safeStatus` (pre-existing, built for the My Status page). This sprint added the remaining spec-required helpers directly to that file (kept single source of truth rather than forking a second file):
`safeNumber` (alias of `safeNum` for naming parity), `safeBoolean`, `safePrice` (alias of `safeCurrency`), `safeTime` (datetime vs `safeDate`'s date-only), `safeRequestId`.

`safeStatus` already includes a label map that formats enums like `paid_pending_approval` → "Awaiting admin approval", and falls back to Title Case (`customer_pays_provider_directly` → "Customer Pays Provider Directly") for any key not in the explicit map — verified this fallback logic directly satisfies the spec's example.

## super-admin
No equivalent file existed (`lib/status-labels.ts`/`lib/field-labels.ts` cover label maps, not null-safety). Created `lib/api-foundation/normalize.ts` this sprint with the full spec set: `safeNumber, safeText, safeBoolean, safeCurrency, safePrice, safePercent, safeDate, safeTime, safeArray, safeRequestId, safeStatus`. Same fallback-to-Title-Case behavior as tenant-portal's `safeStatus`.

## Used in the two smoke pages
- `app/admin/home-services/overview/page.tsx` imports `safeNumber, safeText` from the new `normalize.ts`.
- `app/(tenant)/provider/status/page.tsx` imports `safeNum, safeArray` from the existing `status-format.ts` plus `blockerMeta` for enum→label mapping.

## Files
- `g:\serviceos\frontend\super-admin\lib\api-foundation\normalize.ts` (new)
- `g:\serviceos\frontend\tenant-portal\lib\status-format.ts` (extended with 5 new exports)
