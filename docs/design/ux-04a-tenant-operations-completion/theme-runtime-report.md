# Theme Runtime Report

All 7 new UX-04A components use `var(--*)` design-system tokens
exclusively (`--border`, `--text-secondary`, `--brand`, `--success-text`,
`--warning-text`, `--danger-text`, `--radius-md`, `--radius-full`,
`--radius-sm`), same as the 10 UX-04 baseline components — confirmed by
source review (grep for hex literals across
`components/ux04/*.tsx` found none). No component sets an explicit
light/dark value itself; theming is fully delegated to whatever the
design-system's `ThemeProvider` (verified passing in
`ux01-forward-certification.md`) resolves those tokens to. No live
browser toggle-and-screenshot check was performed this pass (same
limitation as `ssr-hydration-report.md` — no headless browser available).
