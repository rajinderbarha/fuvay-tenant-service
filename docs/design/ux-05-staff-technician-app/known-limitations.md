# Known Limitations (through Round 3)

- **`StaffHomeScreen`/`StaffWorkQueueScreen` remain honest placeholders.** No live staff work-queue-summary
  endpoint exists (confirmed across all three rounds) — this is a genuine backend-contract gap, not a frontend
  omission; nothing more can be built here without either a real endpoint or an explicit product decision.
- **`NotificationCard` and `NextActionBar` are built but only partially wired.** `NextActionBar` is used in the
  new `CurrentJobScreen` but not in `JobDetailScreen` (kept as its own inline action grid, unchanged, to avoid
  touching the one screen with the real, money-touching `complete` action more than necessary this round).
  `NotificationCard` is unused — `NotificationsScreen` keeps its own pre-existing renderer.
- **`NetworkStatusBanner` is demonstrated in a dev showcase but not wired into any production screen.** No real
  network-state detection (e.g. `NetInfo`) is wired up anywhere in the app; the banner takes a fixture
  `OfflineSyncStateView` in its showcase.
- **Draft persistence remains unimplemented** everywhere it's mentioned (Inspection/Checklist, Notes/Media,
  Quote) — all `useState`-only, lost on unmount. Disclosed consistently since Round 2.
- **Playwright *runtime* verification hit a specific, real, diagnosed blocker this round.** The Expo web
  **build** (Metro bundling) is proven to work end-to-end — verified HTTP 200 + a real 3.1MB bundle containing
  this round's actual compiled source. The **runtime** check (load the bundle in an actual browser, watch for
  console errors) could not run: headless Chromium crashes with `SIGSEGV` because required OS shared libraries
  aren't installed in this WSL image, and installing them needs `sudo`, which requires a password not available
  here (`sudo -n true` → `sudo: a password is required`). This is a diagnosed environment constraint specific to
  this WSL image, not a claim about the app's correctness in a real browser.
- **Pre-existing type errors remain unfixed** (19 total now — 14 pre-existing before UX-05, 5 new occurrences of
  the identical existing `useCallback`/`useAction`/screen-prop-typing pattern reused verbatim in this round's new
  files). See `typecheck-report.md` for the itemized, re-verified-fresh list. Fixing the shared
  `hooks/useApi.ts` generic-inference root cause remains out of scope (touches a hook every existing screen
  depends on, no dedicated regression coverage exists for it).
- **Most of the 72-file documentation set remains unwritten** (37 of 72 done through Round 3).
- **~23 of the original ~30 dev-showcase-screen targets remain unbuilt** (7 built so far: Parts Request,
  Inspection & Checklist, Notes & Media, Staff Parts Approval, Quote, Offline States, plus Current Job as a
  semi-production screen). Session-expired/tenant-suspended/light-dark-theme/large-text-accessibility dedicated
  showcases were not built as separate screens.
- **Staff Work Queue / More / Parts Approval remain correctly restricted, showing almost nothing** — intentional
  (fail-closed `deriveRole()` + no live StaffPermission endpoint), not a half-built feature.
