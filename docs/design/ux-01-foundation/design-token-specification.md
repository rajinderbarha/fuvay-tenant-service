# Design Token Specification

Source of truth: `frontend/packages/design-system/src/tokens/*.ts` (typed,
importable in component logic) mirrored by CSS custom properties in
`src/theme.css` and each app's existing `globals.css`.

## Color
Semantic pairs (light/dark resolved via `[data-theme]`): `bg`, `bg-soft`,
`bg-muted`, `surface`, `surface-elevated`, `surface-sunken`, `border`,
`border-strong`, `border-focus`, `text-primary/secondary/tertiary`,
`text-on-brand`, `brand`/`brand-hover`, `accent`/`accent-hover`, `success/
warning/danger/info/neutral` (+ `-bg`/`-border`/`-text` variants each),
`focus-ring`, `overlay`, `skeleton`. Chart series colors are a literal hex
array (`chartPalette.light/dark`, 8 colors) since canvas/SVG chart libraries
can't reliably read CSS vars per-datapoint.

## Typography
`typeScale` in `tokens/typography.ts`: display, pageTitle, sectionTitle,
cardTitle, body, bodyCompact, label, helper, caption, badge, tableHeader,
tableCell, numeric, code — each with size/weight/line-height/letter-spacing,
mirrored as `.ds-text-*` utility classes in `theme.css`.

## Spacing / Radius / Elevation / Breakpoints
4px-based `space` scale (0–20), `radius` (sm→full), `elevation` (sm/md/lg/
overlay shadow presets, distinct dark-mode shadow opacities), `breakpoints`
(sm 480 / md 768 / lg 1024 / xl 1280 / xxl 1536).

## Motion
`duration` (instant/fast/base/slow), `easing` (standard/decelerate/
accelerate), and `motionDuration(ms)` helper that returns `0` under
`prefers-reduced-motion: reduce`. `theme.css` also globally zeroes animation/
transition durations under that media query as a safety net.

## Status registry
`statusRegistry` in `tokens/motion.ts` — the single place status→tone
mappings are defined (see `status-system.md`).
