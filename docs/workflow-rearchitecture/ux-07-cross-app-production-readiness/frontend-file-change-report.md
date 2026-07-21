# Frontend File Change Report

Exactly one frontend source file changed this round:

- `mobile/customer-app/src/lib/chatLanguages.ts` — narrowed `CHAT_LANGUAGES`
  from a 14-entry BCP-47 registry to exactly 3 entries
  (en/hi/pa = English/हिन्दी/ਪੰਜਾਬੀ), per this phase's explicit requirement.
  Grep-confirmed sole consumer: `mobile/customer-app/src/screens/DeepSeekChatScreen.tsx`.
  No other file imports this module. See `smartbot-language-verification.md`
  for the full rationale and what was NOT changed (the selector UI itself,
  the `withLanguageInstruction()` mechanism).

No other frontend file (super-admin, tenant-portal, mobile/staff-app, or
any other mobile/customer-app file) was modified in Round 1.

## Round 2

Exactly one additional frontend file changed:

- `frontend/tenant-portal/package.json` — added
  `"@testing-library/dom": "^10.4.0"` as an explicit devDependency (a
  missing peer dependency of the already-pinned
  `@testing-library/react@^16.0.1`). See `frontend-corrections-report.md`
  for full justification. This is the ONLY code change made in Round 2 —
  every other Round 2 change is a new or appended documentation file.

No other frontend file was modified in Round 2. A real, precisely-diagnosed
React-version-pin mismatch was found in the SAME file
(`frontend/tenant-portal/package.json`'s `react`/`react-dom: 19.2.7` vs
`frontend/super-admin/package.json`'s `19.2.0`) but was deliberately NOT
changed this round — see `frontend-corrections-report.md`'s "Correction
considered but NOT made" section for the full reasoning.
