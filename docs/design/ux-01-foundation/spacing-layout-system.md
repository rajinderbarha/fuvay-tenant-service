# Spacing & Layout System

4px-based scale: `0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80` px (`space[0..20]`
in `tokens/spacing.ts`, mirrored as `--space-*` vars). Components use these
directly in inline styles (no Tailwind, matching the existing app
convention) rather than arbitrary pixel values.

## Layout primitives
- `PageShell` — max-width 1400px, centered, `1.5rem` padding, vertical stack.
- `PageHeader` — title + description + right-aligned actions, wraps on
  narrow viewports.
- `Section` — optional title/actions row + content stack, `0.75rem` gap.
- `Card` — bordered surface with optional header (`title`+`actions`) and
  configurable padding (`none/sm/md/lg`).

## Radius scale
`sm 4px / md 8px / lg 12px / xl 16px / full 9999px` — buttons/inputs use
`md`, cards/modals use `lg`, pills/badges use `full`.
