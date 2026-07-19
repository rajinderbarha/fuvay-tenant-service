# Filter + Saved-View System

Implemented inside `EnterpriseListPage` (`ListFilterOption[]` prop) — not a separate component in
this phase; each list-page instance supplies its own filter set.

## Applied vs draft
Filter chips reflect only *applied* filters (values selected and confirmed); draft selections in
an open filter control are not yet chips. On mobile, filters open in a drawer (design-system
`Drawer`) rather than an inline panel.

## Saved views
MOCK ONLY. No persistence layer exists — "save this view" is a UI affordance only in this phase;
selecting a saved view does not survive a reload and there is no backend endpoint for it. This is
called out explicitly wherever the affordance would appear so it is never mistaken for a working
feature. See `product-decisions-required.md` for whether saved views become a real feature.

## Chip removal
Each applied-filter chip is individually removable; removing the last chip for a filter key clears
that filter back to "All".
