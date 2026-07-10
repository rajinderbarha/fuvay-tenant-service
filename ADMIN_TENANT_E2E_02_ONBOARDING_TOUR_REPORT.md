# Onboarding Tour Interference Fix Report (Part 5)

## Component
`hooks/useTour.ts` — 7-step tour, dismiss-persistence via `localStorage["serviceos-admin-tour-done"]`.
Rendered by `components/tour/TourGuide.tsx` when `tour.mounted && tour.active`.

## Fix applied
Added two independent escape hatches in `useTour.ts`'s mount effect:
1. `process.env.NEXT_PUBLIC_DISABLE_TOUR_FOR_E2E === "true"` — build-time env var, for CI/dev
   servers that always want the tour off.
2. `localStorage["serviceos_disable_tour_e2e"] === "true"` — runtime flag the Playwright harness
   can set via `page.addInitScript()` BEFORE any navigation, no server restart needed.
Either flag skips `setActive(true)` entirely, so the tour never mounts and never overlays nav
items during automated route testing.

`e2e-admin-tenant/e2e/helpers/auth.ts`'s `loginViaUi()` now calls
`page.addInitScript(() => localStorage.setItem('serviceos_disable_tour_e2e', 'true'))` before
`page.goto('/login')`, so every test using `loginAsSuperAdmin()` (the shared helper) is
automatically tour-free.

## Dismiss-persistence verified
`complete()`/`skip()` write `localStorage["serviceos-admin-tour-done"] = "true"`; `useTour`'s
mount effect checks this key and does not reactivate — confirmed by code read (existing,
correct); not independently re-tested since the E2E flag now bypasses this path entirely.

## Browser verification
All 26 tests in `admin-shell-e2e02.spec.ts` (dashboard load, nested-route active-state, route
smoke, responsive) ran clean with no tour overlay blocking any locator or screenshot — confirms
the fix works end-to-end in a real browser session.
