# Customer App — Testing Strategy

## Stack

- **Jest** (`jest-expo` preset) — test runner, RN-aware transform.
- **React Native Testing Library** + `@testing-library/jest-native` —
  component rendering and accessibility-aware queries (`getByRole`,
  `getByLabelText`).
- Existing `tests/test_customer_app.py` (Python, file-existence assertions)
  is unrelated to this suite and untouched.

## What Is Covered This Sprint

| Area | File(s) | What it verifies |
|---|---|---|
| Theme tokens | `design-system/__tests__/theme-tokens.test.ts` | all 52 required semantic keys present in both themes, identical key structure, valid color values, dark theme is a real distinct palette (not a hue tweak), dark shadow color differs from light |
| Theme provider | `design-system/__tests__/theme-provider.test.tsx` | system-mode resolution, explicit light/dark override, persistence across mounts, safe fallback on corrupted persisted value |
| API errors | `api/__tests__/api-errors.test.ts` | every HTTP status → category mapping, timeout, cancelled, network error, retryability, no raw server message leaks, request-id passthrough |
| Preference storage | `storage/__tests__/preference-storage.test.ts` | save/read/remove, missing key, corrupted JSON recovery, `clearAll` scoping, adapter-failure handling |
| Logging | `observability/__tests__/logger.test.ts`, `redaction.test.ts` | level gating by environment, redaction of tokens/OTP/passwords/PII before reaching `console.*`, crash-adapter routing, safe correlation metadata retained |
| Environment | `config/__tests__/environment.test.ts` | safe local fallback, production throws on missing/localhost URL or mock mode, valid production config accepted |
| Primitives | `components/__tests__/*.test.tsx` | AppText, AppButton, AppIconButton, AppTextField, AppCheckbox, AppSwitch, AppCard, EmptyState, ErrorState — render, press/toggle behavior, disabled/loading behavior, accessibility role/label/state |

## What Is Not Covered This Sprint

- No device-level manual VoiceOver/TalkBack pass (no physical device/simulator exercised).
- No visual regression / screenshot testing.
- No E2E test (no Detox/Maestro configured — none existed before this
  sprint and adding one is out of scope for an architecture baseline).
- Existing 19 screens are not unit-tested (pre-existing gap, not introduced
  by this sprint).

See `known-gaps.md` for the full list with severity.

## Running

```bash
cd mobile/customer-app
npm install
npm run typecheck
npm run lint
npm run format:check
npm test              # jest
npm run test:coverage
```

## Conventions

- One `__tests__` folder per module area, colocated (`design-system/__tests__`,
  `api/__tests__`, etc.) rather than a single top-level `__tests__` tree —
  keeps tests next to the code they verify.
- Component tests always render through `src/testing/render-with-theme.tsx`
  (`renderWithTheme`) since every primitive requires `ThemeProvider` context.
- Prefer `getByRole`/`getByLabelText` over `getByTestId` when the query is
  really an accessibility assertion in disguise.
