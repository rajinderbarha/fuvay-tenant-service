# E2E-07 Tenant Responsive Baseline Report
**Date:** 2026-07-10  
**Analysis:** Static analysis of CSS / layout patterns — browser verification pending

---

## Responsive Design Approach

The tenant portal uses inline styles with CSS variables (design-system approach from Sprint 34B). No Tailwind classes remain in tenant pages (removed in Sprint 34).

### Layout Breakpoints

**Sidebar:**
- Collapsed: ~22px wide (icons only)
- Expanded: ~260px wide
- Toggle via `ChevronLeft`/`ChevronRight` button in topbar

**Main content:**
- Uses `maxWidth` constraints (typically `1120px–1200px`) with `margin: "0 auto"` for centering
- Padding: `24px 28px` on most pages

**Tables / Grids:**
- `EnterpriseDataGrid` renders in a scrollable container with `overflow-x: auto`
- Column widths defined in pixels; table scrolls horizontally on small screens

**Cards / KPI Grids:**
- `display: grid` with `gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))"` — auto-responsive
- `gap` values consistent (10–16px)

### CSS Variables Used

All colors, borders, backgrounds from design-system variables:
- `--text-primary`, `--text-secondary`, `--text-tertiary`
- `--surface`, `--surface-sunken`
- `--border`, `--brand`
- `--success`, `--warning`, `--danger` (with `-bg`, `-border`, `-text` variants)

### Dark / Light Theme

`useTheme` hook toggles `data-theme="dark"` on `<html>`. CSS variables in `globals.css` have both light and dark values.

### Known Responsive Limitations

1. Mobile (<768px) is not a primary target for the tenant owner portal (admin/desktop use case)
2. Staff portal (separate shell in `components/layout/StaffLayout.tsx`) is more mobile-optimized
3. No media queries in tenant pages — relies on sidebar collapse for space savings

### Findings

| Check | Status |
|---|---|
| Sidebar collapse for narrow screens | PASS |
| Table horizontal scroll | PASS |
| KPI grid auto-layout | PASS |
| CSS variables (no hardcoded colors) | PASS |
| Dark mode support | PASS |
| Mobile-first | NOT APPLICABLE — desktop portal |

**Status: PASS** — Responsive baseline meets desktop portal standards. Mobile is out of scope for tenant owner portal.
