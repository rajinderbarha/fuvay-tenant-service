# FINAL-L5-03 — Loading and Empty State Report

## Real bug found and fixed this sprint: invalid HTML nesting causing hydration mismatches
`Skeleton` (renders a `<div className="skeleton">`) was placed directly inside `<p>` tags in 3 places on the Tenant Dashboard (`app/(tenant)/dashboard/page.tsx`, lines formerly 182, 275-277, 287-289, 294-296). A `<div>` cannot be a child of `<p>` per the HTML spec — browsers auto-close the `<p>` early during parsing, which differs from what React's SSR output describes, causing a real, browser-console-confirmed hydration mismatch and forcing React to discard and client-re-render that entire subtree on every dashboard load (a real, if modest, performance cost — see Performance Code Cleanup Report).

**Fix**: changed the 3 wrapping `<p>` elements to `<div>` (zero visual change — all styling was inline, no `<p>`-specific browser defaults were relied on).

**Verification**: real Chromium regression before/after — hydration-mismatch console errors present before the fix, confirmed absent after (`final-l5-03-cross-app-regression.spec.ts`, Tenant Portal test, console-error capture).

## Rules checked
1. Loading must not cause major layout shift — `Skeleton width={}/height={}` props are set to match the real content's approximate size at each of the 3 fixed sites; no shift observed in the browser regression.
2. Empty state must explain what it means — spot-checked (`EmptyState` component, 17-18 consumers per app per FINAL-L5-00's sampled inventory) — consistent pattern, not re-audited exhaustively this sprint.
3. Empty state offers a next action — confirmed for Customer bookings empty state ("Book Now" CTA, verified live in FINAL-L5-02B).
4. No fake rows during loading — confirmed, `Skeleton` placeholders are visually distinct (shimmer style), never real-looking fabricated data.
5. No blank white screens — not found in this sprint's scan (every loading path checked shows either a page skeleton or an inline spinner).
6. No spinner-only full-page loading for complex screens where skeletons fit better — Dashboard/Jobs/Bookings all use `Skeleton`, not full-page spinners; not exhaustively re-audited across all ~100+ pages in each app.

## Result
The one real, concrete defect found (invalid Skeleton/`<p>` nesting) is fixed and verified. Broader loading/empty-state consistency across every page in 3 apps was not exhaustively re-audited this sprint (would require opening every page) — spot checks found no other instances of the same bug pattern (confirmed via a codebase-wide regex scan for `<p...>{...Skeleton` — 0 remaining matches after the fix).
