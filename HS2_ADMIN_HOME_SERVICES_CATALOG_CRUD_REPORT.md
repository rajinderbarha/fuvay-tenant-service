# HS2 — Catalog CRUD Report

## Confirmed real, pre-existing CRUD (unchanged this sprint)
- Create/edit master service: via `/admin/catalog-module/master-services`
  (linked from "Add Service" and each service's "View" action).
- Types/brands behavior toggles (`can_override_price`/`is_routing_only`):
  previously mutable from the catalog page's Brands tab; **this sprint
  removed the inline toggle UI** along with the pricing form (see Scope
  Report) since it was bundled with the pricing form being removed —
  behavior toggling now needs to happen from the master-services page.
  This is a **regression in convenience, not data-loss** (the underlying
  `MasterServiceBrand.can_override_price`/`is_routing_only` fields and
  their API are untouched), but it does mean HS2 shipped with slightly
  less inline CRUD than before. Documented in blockers.
- Issues/Options: real read-only lists in-page with "Manage in Issue
  Types →" / "Manage in Service Options →" links to their dedicated
  admin pages (pre-existing, unchanged).
- Activity: real read-only audit feed (pre-existing, unchanged).

## Not built this sprint (ticket-required, missing)
- Service **Group** CRUD (Create/Edit/Activate/Deactivate/Reorder Group)
  — no UI exists for this at all, in the catalog page or elsewhere found
  during this sprint's inspection. The catalog page only *reads* groups
  (`listApi.data?.groups`) to organize the left panel; there is no
  "Add Service Group" modal.
- Service Type CRUD from within the catalog UI (add/edit/deactivate/
  reorder/delete-if-unused) — types are currently read-only in the
  Types tab; adding one requires going outside this console (location
  not verified this sprint).
- Brand CRUD from within the catalog UI — same gap; brand
  *behavior toggles* existed before this sprint but were removed
  alongside the pricing form (see above); no add/reorder UI found.
- Issue/Question and Option/Add-on CRUD **inside** the catalog console
  (they link out to dedicated pages instead, which is arguably
  acceptable per the ticket's "or map actual routes" allowance, but the
  ticket's own CRUD checklist implies these should be manageable inline).

## Delete safety rule
Not independently verified this sprint whether hard-delete is blocked
for in-use catalog records with the ticket's exact message ("This
catalog item is already used. Deactivate it instead to keep history
safe.") — no delete action exists in the catalog console UI itself
(delete, if it exists at all, would be on the linked-out management
pages, which were not inspected this sprint).

## Verdict
CRUD: **partial**. Read operations and pre-existing service-level edit
(via link-out) are real. Group CRUD, inline Type/Brand CRUD, and
delete-safety verification are **not implemented/verified** this sprint
— the single highest-priority fix (removing pricing from the catalog)
consumed the sprint's time budget.
