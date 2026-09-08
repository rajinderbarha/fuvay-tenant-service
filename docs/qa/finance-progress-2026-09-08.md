# Finance progress repair — 2026-09-08

## Observed on the public tenant page

- Cash and UPI enabled, invoice name and prefix entered, but finance showed 0% before Save.
- Saving the existing details returned 100% / Ready for review. The sidebar stayed at 83% and Review & Submit remained locked until the page was reopened.
- Reopening confirmed persisted finance completion, overall setup 100% (6/6), and an unlocked Review & Submit link. The profile was **not** submitted for approval.

## Changes

- Show draft completion as fields are edited, explicitly labelled unsaved; only saved backend completion unlocks navigation.
- Notify the actual onboarding shell after a successful save so its progress and prerequisites refresh immediately.
- Show save status and success feedback; preserve entries on failure and disable edits during a save.
- Continue only when the save response confirms `setup_complete`.
- Normalize invoice form defaults and trim submitted invoice text; reject whitespace-only required details before continuing.
- Display load errors with Retry instead of an endless loading skeleton. Cash and UPI now fill the two-column method grid.

## Verification

- Eight regression tests render the real onboarding shell with controlled API responses, including sidebar refresh, failed-save behaviour, persisted completion, and incomplete-response navigation protection.
- Targeted existing backend finance/gate regressions: 21 passed.
- No backend contract or migration change. The public-page save/reopen verification used the existing deployed build; the new draft-progress and automatic-refresh UI changes require deployment.
