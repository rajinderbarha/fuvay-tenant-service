# Round 4 Pass 2 — Customer-App Test Report

## Environment
WSL Debian, clean install each run (`rm -rf node_modules` not needed — fresh
`~/uxc7/customer-app` copy + `npm install --legacy-peer-deps --no-audit --no-fund`,
866 packages, ~30-60s).

## Before (baseline, HEAD b6cdd82, prior to this pass's changes)
- `npx jest`: 5 suites, 48/48 tests passing (matches the UX-06 final-commit baseline
  recorded in the mission brief).
- `npx tsc --noEmit`: 0 errors (verified at HEAD before starting).

## After (this pass, HEAD fd4ac91)
- `npx jest`: **7 suites, 58/58 tests passing** (48 pre-existing + 10 new: 5 in
  `ThemeContext.test.tsx`, 5 in `theme.test.ts`). 0 failures, 0 skips, 0 retries,
  no timeout inflation. Run time ~13.8s.
- `npx tsc --noEmit`: **0 errors**.
- No pre-existing test was modified — the 48 baseline tests run unchanged, confirming
  no regression from the theme foundation or the Login/Home/SmartBot migration.

## New tests added this pass
- `src/context/__tests__/ThemeContext.test.tsx` (5 tests): system-default resolution,
  dark-preference persistence to AsyncStorage key `customer_app_theme_preference`,
  restart persistence (remount with a pre-seeded storage value), light-overrides-dark-
  system-scheme, corrupt-stored-value falls back to `system` rather than throwing.
- `src/styles/__tests__/theme.test.ts` (5 tests): light vs dark bg/surface/text are
  genuinely distinct values; the dark surface hierarchy has >1 distinct color (guards
  against a future "everything collapses to one dark color" regression); dark
  backgrounds are not literally `#000000`; statusBarStyle flips dark/light correctly;
  spacing/font/radius scales are identical across modes (only color should vary).

## Not run this pass (explicitly out of scope / not achievable in session)
- Playwright / Expo-web visual run against live production routes (item 17-18 of the
  mission) — not attempted this session; no `expo export` or Playwright config was
  exercised. This is a real gap, not a silent skip.
- Full responsive-width matrix (320/360/390/430/768/1024) — not measured with actual
  rendered screenshots; only reasoned about via style values (flex/wrap usage).
- Text-scaling, reduced-motion (beyond Skeleton), and full accessibility audit across
  all screens — only the migrated screens/components got real a11y attributes; the
  14 not-yet-migrated screens were not audited this pass.
