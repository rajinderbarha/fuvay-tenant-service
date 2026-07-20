# Breadcrumb Reconciliation

## Status: NOT implemented this slice

`frontend/super-admin/components/layout/Breadcrumbs.tsx` exists and is already wired into `AdminLayout.tsx`. It was not modified this slice. Reconciling breadcrumb labels/hierarchy to the new approved workflow grouping (e.g., "Businesses → Business Detail → Verification" instead of engine-based labels) requires touching the parent-section mapping for many routes at once — a page-consolidation-adjacent change (Workstream 6/8 territory) rather than a routing/access fix, and the 6 nav items added this slice did not require new breadcrumb entries beyond what the existing `Breadcrumbs` component already derives automatically from the URL path (spot-checked: it appears to generate breadcrumbs from path segments rather than a hand-maintained map, so the 6 new pages should already produce a reasonable breadcrumb without any code change — not exhaustively verified against every new page).

## Deferred
Full breadcrumb reconciliation to user-friendly, workflow-grouped labels (not engine names) across all apps, per the brief's examples (Businesses → Business Detail → Verification; Jobs → Service Job → Inspection and Quote; My Work → Work Item → Service Job; Business → Credits → Credit Ledger) — tracked in `deferred-items.md`.
