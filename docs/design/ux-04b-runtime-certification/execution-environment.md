# Execution Environment (UX-04B)

WSL2 Debian, native Linux filesystem copy at `/root/serviceos-ux04a`
(same scratch directory reused from UX-04A within this session, refreshed
via rsync before each verification pass — no need to recreate from
scratch since this session's WSL instance stayed up throughout, unlike
the mid-UX-04A-session host restart). Node v20.20.2, npm 10.8.2.

New this pass:
- `@playwright/test` + `@axe-core/playwright` installed as
  `frontend/tenant-portal` devDependencies; `npx playwright install
  --with-deps chromium` succeeded on the first attempt (downloaded Chrome
  for Testing 149.0.7827.55 + Chrome Headless Shell + FFmpeg, plus apt
  system dependencies for headless Chromium on Debian).
- `frontend/tenant-portal/package-lock.json`'s stale pinned react
  resolution was superseded by re-resolving after the `package.json`
  version fix (see `lockfile-and-toolchain-evidence.md`).

One real environment friction encountered and worked around: manually
backgrounded (`nohup ... &`, `disown`) `next start` processes died
unpredictably between separate `wsl.exe` invocations from the Windows
host tool. Fixed by switching to Playwright's built-in `webServer` option
in `playwright.config.ts`, which manages the server lifecycle within the
same Playwright process — reliable across all runs this pass.
