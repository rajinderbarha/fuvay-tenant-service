# Enterprise Detail Page Pattern

Component: `frontend/super-admin/components/ux02/patterns/EnterpriseDetailPage.tsx`.

## Used by
Tenant 360 (`/dev/ux-02/tenants/[id]`), Compliance Case Detail (`/dev/ux-02/compliance/[id]`) —
2 usages, satisfying "used by Tenant 360 + at least 1 more".

## Props contract
`title`, `subtitle?`, `readiness`, `sections: {id,label,content}[]`, `headerActions?`.

## Behavior
- Desktop: sticky left section nav (`position: sticky`), active section highlighted, button-based
  (keyboard operable, `aria-current`).
- Mobile (<768px, CSS media query swap): sticky nav hidden, replaced by a single `<select
  aria-label="Jump to section">` that jumps `active` state.
- Content area renders whichever section is `active`; no route change on section switch (single
  page, in-memory state).

## Design-system usage
`PageHeader` for the title/readiness tag; no raw hex — colors come from CSS custom properties
already defined by the design-system theme (`--border`, `--accent-muted`, `--brand`, etc).
