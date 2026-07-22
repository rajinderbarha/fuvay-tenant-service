# Customer Source Change Report — Pass 3c

Only one file changed in this pass:

| File | Reason |
|---|---|
| `mobile/customer-app/src/context/__tests__/ThemeContext.test.tsx` | Added a deterministic mock for `Appearance.addChangeListener` (previously unmocked, causing an intermittent race with the real environment's live color-scheme signal) — test-infrastructure fix only. |

No production source file (`ThemeContext.tsx`, any screen, any shared
component) was modified in this pass. No new dependency, script, or config
file was added.

An unrelated drift in `app.json`/`package.json` (Expo SDK/react version
downgrade, caused by an external `expo start` process auto-adjusting
versions) was found in the working tree before this pass began and was
reverted via `git checkout --` without being committed — it is not part of
this pass's change set and predates it.
