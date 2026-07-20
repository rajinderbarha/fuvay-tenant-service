# CUSTOMER-L5-02 — Testing Evidence

```
npx jest
Test Suites: 34 passed, 34 total
Tests:       243 passed, 243 total
```

(212 carried over from CUSTOMER-L5-00/01, 31 new this sprint.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/auth/domain/__tests__/phone-validation.test.ts` | 6 | valid/invalid phone formats matching the backend's own regex, OTP format, normalization |
| `features/auth/domain/__tests__/session.test.ts` | 6 | backend-profile → `CustomerSession` mapping, control-character/whitespace normalization, initials derivation |
| `features/auth/state/__tests__/session-store.test.ts` | 6 | hydrate/persist/clear against real `secure-storage.ts`, profile patch merging |
| `features/auth/state/__tests__/session-bootstrap.test.ts` | 4 | guest with no tokens, authenticated with valid tokens, 401→refresh→guest fallback, transient-network-failure resilience |

## Not Covered

- No component tests for `OtpLoginScreen`/`ProfileScreen` (same rationale
  as CUSTOMER-L5-01's system screens — pure logic prioritized).
- No integration test against a real/mocked HTTP server exercising the full
  `/otp/send` → `/otp/verify` → `/me` round trip — each API call is
  exercised individually via the mocked `authApi` in
  `session-bootstrap.test.ts`, and `auth-api.ts` itself is a thin,
  directly-inspectable wrapper over `apiClient` (already tested in
  CUSTOMER-L5-00's `api-errors.test.ts`).
- No device-level test of secure-storage persistence surviving an app kill
  (requires a physical device/simulator).
