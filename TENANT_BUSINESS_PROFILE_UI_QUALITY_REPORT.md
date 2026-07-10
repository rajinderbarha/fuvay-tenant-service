# Tenant Business Profile — UI Quality Report

## Structure delivered (matches the reference description)

1. Breadcrumb (Settings / Business Profile)
2. Enterprise header (title, subtitle, 3 top-right actions)
3. Hero card: dark gradient cover banner (reuses storefront photo when set,
   falls back to a premium dark gradient — never a fabricated stock image),
   business logo overlapping the cover, business name + verified checkmark,
   category/plan/status badges, SVG completion ring (color-coded by
   percentage), last-updated/slug/bookable meta chips
4. "Complete your profile" missing-requirements card grid (icon + title +
   Missing badge + Add Now/Upload action per item, "View all" link when >4)
5. Horizontal tab bar (6 tabs, blue underline on active) — Overview, Legal &
   Verification, Address & Service Areas, Branding & Media, People & Access,
   Activity
6. Overview tab: 2-column layout — Business Information card (read-only
   display + Edit button) on the left; Quick Summary + Next Steps stacked on
   the right
7. Edit Business Info modal (dirty-state tracking, disabled Save until
   changed, loading state, inline error with request_id)
8. Preview Public Profile modal (customer-safe fields only)

## Visual design notes

The existing app uses a light/neutral enterprise theme (CSS custom
properties like `--surface`, `--text-primary`) rather than a system-wide
dark theme — the hero card specifically uses a dark gradient treatment
(`#1e293b` → `#0f172a`) to match the reference image's premium dark banner
look, while the rest of the page stays consistent with the app's existing
light enterprise theme (glass cards, soft borders, subtle shadows) rather
than converting the entire portal to dark mode, which would be a
much larger, separate design-system change out of this ticket's scope.

## No longer a "basic form page"

Old page: single scrolling form with Personal Profile / Business Profile /
Address / Media / Completion / Verification / Activity all stacked as plain
cards, all fields always editable inline. New page: hero identity card with
visual completion ring, a dedicated action-oriented missing-requirements
grid, tabbed information architecture separating concerns (legal vs. address
vs. media vs. people vs. activity), and a proper edit-modal flow separating
"view" from "edit" — a materially different, enterprise-grade console.

## Real data, no fabrication

Every number shown (completion %, item counts, team member list, service
area list, activity feed) comes from already-fetched real API responses.
Fields the platform genuinely doesn't support yet (PAN Number, Business
Registration Number, Gallery Images, Cover Photo upload) are shown as
honest "not yet collected/supported" states, never fake placeholder data.
