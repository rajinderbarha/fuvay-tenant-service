# Deferred Enhancements (Round 1 -> Round 2+)

- Simplify the SmartBot language-selector modal UI itself (currently still
  has a search box sized for the old 14-language registry; could become a
  true 3-button one-tap layout now that the registry is narrowed to 3).
- Find/seed a super_admin demo credential and verify super-admin login +
  its view of the same demo tenant/job used in this round's E2E proof.
- Continue the E2E proof job (`JOB-20260721-000008`, currently `accepted`)
  through the remaining real transitions: onTheWay -> reachedSite ->
  inspection -> quote/parts -> completion -> commission -> review.
- Add `offering_type_id` to the booking draft's `required_fields` response
  (backend-owned fix, flagged not built) OR add an unscoped fallback
  `ServicePricingRule` for `ac_repair` (a catalog-config change, also not
  this session's scope).
- Full WSL fresh-install + `tsc --noEmit` + `npm test` sweep across all 4
  apps, including a stability check on the `chatLanguages.ts` change.
- Playwright-driven UI screenshots for the same or an equivalent cross-app
  record, across all 4 apps' real production screens.
- Full mock/fixture census, error/recovery state audit, responsive/
  dark-mode/accessibility certification sweeps.
- Duplication review between tenant-portal's `/staff/*` routes and
  mobile/staff-app's screens.
