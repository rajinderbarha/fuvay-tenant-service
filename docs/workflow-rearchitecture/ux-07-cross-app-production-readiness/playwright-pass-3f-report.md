# UX-07 Pass 3f — Playwright / Visual Evidence

## What was attempted and what worked

1. `npx expo export -p web --output-dir <dir>` — **succeeded**. The app
   bundles for web (react-native-web + react-dom are real dependencies of
   this app, confirmed in `package.json`). Output: `index.html`, a
   1.4MB JS bundle, and font/icon assets. Metro bundled 643 modules in
   ~24s with no errors.
2. Served the export with `python3 -m http.server 4173` inside the same
   WSL environment used for the test/typecheck runs.
3. Ran real Playwright (`chromium`, version 1.61.1, a system install
   already present in the WSL image at `/usr/bin/playwright`) against
   `http://localhost:4173/` and captured full-page screenshots at a
   412x915 viewport:
   - `screenshots/default-light.png` — default OS color scheme.
   - `screenshots/default-dark.png` — Playwright browser-context
     `colorScheme: 'dark'` emulation.

Both screenshots show the real rendered **LoginScreen** (the app's actual
root route when no session exists) and genuinely demonstrate the theme
system working in a browser: the sign-in card switches from a light
surface with dark text to a dark surface with light text between the two
captures, while the brand-blue top banner keeps its brand color in both
(consistent with `ThemeContext`/`theme.ts`, which does not theme the
brand-color token itself).

Per the coordinator's mid-task correction, **no width-specific
(320/390px) certification screenshots were taken** — only this one
representative mobile viewport, since exact pixel widths are not
meaningful with the design due to change.

## What did NOT work — Home / SmartBot / bottom-nav evidence

Capturing Home, the SmartBot screen, the booking-flow modal, or the
5-tab bottom nav requires an authenticated session, which requires a
reachable backend. In this worktree:

- `http://localhost:8000` (the app's local-dev default) — connection
  refused, no backend process running.
- The only other API URL configured in `.env` is a stale ngrok tunnel
  URL, which returned HTTP 404 on `/docs` (tunnel likely reused for a
  different service or expired).

No backend was started this pass — starting the full ServiceOS backend
stack (DB migrations, seed data, auth) was judged out of this pass's time
budget and orthogonal to its actual goal (accessibility remediation +
whatever visual evidence is realistically achievable). This is reported
honestly rather than substituted with a fabricated screenshot or a mocked
authenticated state dressed up as "real."

## Bottom line

- Web rendering **does work** via Expo web export — this is now
  confirmed, reusable infrastructure for a future pass that does have a
  reachable backend.
- 2 real screenshots exist on disk (`screenshots/default-light.png`,
  `screenshots/default-dark.png`) proving the export renders and the
  theme system functions in a browser.
- Home/SmartBot/bottom-nav visual evidence is **not captured** this
  pass. The accessibility remediation work in
  `accessibility-remediation-report.md` stands on its own (source-level
  fixes + unit test coverage), independent of this visual-evidence gap.
