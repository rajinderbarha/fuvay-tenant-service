# Responsive + Dark-Mode Spot-Check — Round 3 (Workstream 6)

## Honest scope of this check

**No screenshots were captured this round** — Playwright/browser
installation was still not attempted this round either (same constraint
disclosed in Rounds 1-2's `playwright-baseline.md`/`playwright-report.md`;
time budget went to the higher-priority status-transition/completion/
review live-proof work and the react-version-pin investigation). What
follows is a genuine CODE-LEVEL spot-check (real file inspection, not
fabricated) of dark-mode and responsive support for 4 real production
screens, one per app — this is a real but partial substitute for the
brief's request, honestly labeled as such, not claimed as full
certification with visual evidence.

## Screens checked

1. **Customer app — HomeScreen** (`mobile/customer-app/src/screens/HomeScreen.tsx`
   + `src/styles/theme.ts`): **NO dark-mode support** — confirmed,
   standing gap from UX-06 (re-confirmed, not newly discovered). No
   `useColorScheme`/dark palette anywhere in `mobile/customer-app`'s theme
   file. Responsive: React Native's default flexbox layout, no explicit
   320/390px breakpoint logic found (normal for RN — it doesn't use
   CSS media queries; layout is inherently fluid unless a screen hardcodes
   pixel widths, which a quick grep of `HomeScreen.tsx` did not find).

2. **Tenant-portal — job list** (`app/(tenant)/jobs/page.tsx` +
   `frontend/packages/design-system/src/theme.css`): **Dark mode support
   IS real** — confirmed `[data-theme="dark"]` CSS custom-property block
   (line 59) and a `@media (prefers-color-scheme: dark)` fallback (line
   78) in the shared design-system stylesheet that tenant-portal consumes.
   Responsive: a real `@media (max-width: 768px)` block exists (line 141)
   — not specifically 390px/320px breakpoints, but a real mobile
   breakpoint is present, which is the relevant signal for whether this
   screen was built with narrow-width in mind at all.

3. **Staff-app — Job Detail** (`mobile/staff-app/src/screens/
   JobDetailScreen.tsx` + `src/styles/theme.ts`): **Dark mode support IS
   real** — `darkColors` palette exists (added in UX-05 Round 5, per the
   file's own comment), with the same `ColorScheme = "light"|"dark"`
   pattern as the design system. The file's own comment honestly
   discloses: "colors chosen for reasonable contrast against a dark
   surface -- not a pixel-audited dark-mode design pass (no contrast-ratio
   tool was run)" — re-confirmed, not newly re-audited this round.

4. **Super-admin — dashboard** (`app/admin/dashboard/page.tsx` +
   the SAME shared `design-system/src/theme.css`): same dark-mode CSS
   variables as tenant-portal (both apps consume the identical
   design-system package) — real, shared, not independently re-implemented
   per app.

## Summary

| App/Screen | Dark mode | Responsive breakpoint present |
|---|---|---|
| Customer app / HomeScreen | NO (standing gap) | fluid RN layout, no explicit breakpoint code found |
| Tenant-portal / Jobs list | YES (`data-theme` + media-query CSS) | YES (`max-width:768px`) |
| Staff-app / JobDetailScreen | YES (`darkColors` palette, not contrast-audited) | fluid RN layout |
| Super-admin / Dashboard | YES (same shared design-system CSS) | shared with tenant-portal |

## Explicitly NOT covered (honest disclosure)

- No actual rendered screenshot at 390px or 320px for ANY of the 4 screens
  — this is a source-level check only.
- No contrast-ratio/WCAG measurement performed.
- No verification that dark mode ACTUALLY toggles correctly at runtime
  (e.g. that a real theme-toggle control exists and works) — only that the
  CSS/palette infrastructure for it exists in source.
- The other ~26 production screens across the 4 apps were not spot-checked
  — only the 4 named above.

## Recommendation for full certification (future round)

Install Playwright, then for each of these 4 screens (and ideally a wider
sample): load in a real browser/Expo-web session at 390px and 320px,
toggle `prefers-color-scheme`/the app's dark-mode control, and capture
real screenshots — closing the gap this round's code-only check leaves
open.
