# Light & Dark Theme Specification

Both themes live in one file (deviation from the suggested split, noted per
brief) because they share every token name and only differ in value — a
single file makes the pairing easy to audit.

## Mechanism
`[data-theme="light"]` / `[data-theme="dark"]` attribute on `<html>`,
matching the convention already established in both apps' `globals.css`
(this pass did not invent a new mechanism). `@serviceos/design-system`'s
`theme.css` is additive: it does not redefine `--bg`/`--surface`/
`--text-primary` etc. (already correct in both apps), it only adds the new
tokens the design-system introduces (focus ring, overlay, skeleton, neutral
tone, spacing/radius/motion/typography scale).

## Light theme
Backgrounds: white/soft-gray gradient. Surfaces: white with `1px` `#E2E8F0`
borders. Text: near-black primary (`#0F172A`) down to muted gray tertiary.
Brand: blue `#2563EB`. Semantic success/warning/danger/info use saturated
solid hues on pale tinted backgrounds. Shadows are soft, low-opacity black.

## Dark theme
Backgrounds: charcoal slate (`#111827`/`#0F172A`), never pure black.
Surfaces: `#1F2937`/`#243244`. Text: near-white primary down to muted
`#64748B` tertiary. Brand/semantic colors shift to lighter, higher-luminance
variants (e.g. brand `#60A5FA`) with semi-transparent tinted backgrounds
instead of solid pale ones (`rgba(x, 0.12)` pattern) so surfaces don't look
washed out. Shadows are deeper and more opaque to read against dark
surfaces.

## New tokens added this pass (both themes defined in `theme.css`)
`focus-ring`, `overlay`, `skeleton`, `neutral`/`neutral-bg`/`neutral-border`/
`neutral-text`, `info-bg`/`info-border`/`info-text`. Each has an explicit
light default in `:root` and dark override in `[data-theme="dark"]`, plus a
`@media (prefers-color-scheme: dark)` fallback for the rare case an app
embeds a design-system component before `data-theme` is set.
