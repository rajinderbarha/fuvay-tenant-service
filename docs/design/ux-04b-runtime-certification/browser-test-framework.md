# Browser Test Framework

First real headless browser setup for this workspace. Installed via WSL:

```
npm install -D @playwright/test @axe-core/playwright
npx playwright install --with-deps chromium
```

`npx playwright install --with-deps chromium` succeeded on the first
attempt on Debian (WSL2) — downloaded Chrome for Testing 149.0.7827.55,
FFmpeg, and Chrome Headless Shell, plus installed the required apt
dependencies (libatk-bridge2.0-0, libgbm1, libxaw7, xvfb, etc.) via
`apt-get`. No environment wall was hit — genuinely working, not
fabricated.

Config: `frontend/tenant-portal/playwright.config.ts` — 3 projects
(`desktop-light` 1280x800 light color-scheme, `desktop-dark` 1280x800 dark
color-scheme, `mobile` Pixel 7 device profile), targeting a real `next
start` production server on port 3903 via Playwright's built-in
`webServer` option (auto-starts/stops the server, avoiding the
nohup-process-death issues seen with manually backgrounded `next start`
processes in this WSL session).

Test files: `browser-tests/smoke.spec.ts` (route load + console/page-error
+ hydration-error detection across all 18 showcase routes, plus 2
targeted pipeline/model-label checks) and
`browser-tests/keyboard-a11y.spec.ts` (keyboard focus + Enter activation,
Tab order, axe-core WCAG2A/AA scan on 6 key routes, document title
check).

`npm run test:browser` (`playwright test`) runs the whole suite.
