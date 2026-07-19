# Icon System

Library: `lucide-react` (already a dependency in both apps — no new
dependency introduced).

## Rules
- **Sizes**: `16px` inline with body text/buttons, `18-20px` in headers/
  section titles/dialog close buttons, `40px` for empty/error/permission
  state illustrations. Avoid arbitrary in-between sizes.
- **Stroke weight**: use the library default (2px) everywhere; do not pass a
  custom `strokeWidth` — consistency across icons matters more than
  per-icon tuning.
- **Color**: icons inherit `currentColor` via CSS var text tokens
  (`--text-secondary`, `--danger`, etc.) — never a hardcoded hex fill.
- **Icon-only controls**: MUST pass `aria-label` (enforced with a console
  warning in `Button` for `variant="icon"` when missing). Icon-only buttons
  never rely on `title` alone for accessibility.
- **Decorative icons** (e.g. next to a label that already conveys the same
  meaning) get `aria-hidden="true"` so screen readers don't double-announce.
