# Responsive Super Admin Behavior

Breakpoint used throughout UX-02 components: 768px (matches `EnterpriseDetailPage`'s inline media
query; `EnterpriseListPage`'s `mobileCard` swap follows the same breakpoint via the design-system's
existing responsive DataTable behavior from UX-01).

## Patterns
- **List pages**: table on desktop, `mobileCard` render prop below breakpoint (see
  `tenant-list-specification.md`).
- **Detail pages**: sticky left section nav on desktop, `<select>` section-jump on mobile.
- **Filters**: inline filter bar on desktop, `Drawer` on mobile (design-system `Drawer` component).
- **Nav items**: `mobileBehavior` field (`full`/`collapsed_summary`/`hidden_on_mobile`) on every
  `Ux02NavItem` — e.g. Global Search is `hidden_on_mobile` since no mobile command-palette
  interaction has been designed yet.
- **Dashboard**: single-column card grid via `auto-fit minmax(160px,1fr)`, naturally reflows on
  narrow viewports without a separate mobile layout.

## Verification status
Layout has been reviewed only by reading source (MODE B); no real-device or browser-resize
verification has been performed. See `ux01-unverified-gates.md`.
