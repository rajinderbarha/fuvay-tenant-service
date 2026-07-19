# Responsive Behavior Specification

Breakpoints (`tokens/spacing.ts` → `breakpoints`): `sm 480 / md 768 /
lg 1024 / xl 1280 / xxl 1536` (px).

## Component behavior
- `PageHeader`: title/description block and actions row wrap onto separate
  lines below ~`640px` (flex-wrap, no explicit media query needed).
- `Card` grids in the showcase/sample pages use
  `grid-template-columns: repeat(auto-fit, minmax(220-260px, 1fr))` so they
  reflow to 1 column on phones without a breakpoint table.
- `DataTable`: below `768px` (`md`), the `<table>` is hidden and a
  `mobileCard` render-prop stack is shown instead (CSS-only toggle via
  `.ds-datatable-scroll`/`.ds-datatable-cards` in `theme.css`, no JS resize
  listener/layout thrash). Callers that don't pass `mobileCard` simply keep
  the table scrollable horizontally (`overflow-x: auto` wrapper) on narrow
  screens.
- `Modal`: `maxWidth: 90vw` so it never overflows small viewports;
  `Drawer`: `width: min(24rem, 90vw)`.

## Not covered this pass
Fluid typography (`clamp()`-based scaling) and a dedicated tablet layout for
the sidebar shell were not built — both apps' existing sidebar is desktop-
oriented and out of scope to rework here (see `deferred-items.md`).
