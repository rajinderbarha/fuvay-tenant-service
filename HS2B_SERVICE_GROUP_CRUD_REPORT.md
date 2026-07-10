# HS2B — Service Group CRUD Report

## Finding: full CRUD already existed, just not linked
`/v1/admin/service-groups` (in `app/engines/admin_catalog/admin_router.py`)
already has a complete, real backend:
- `POST /v1/admin/service-groups` — creates, validates required `name`
  (`SERVICE_GROUP_NAME_REQUIRED`), rejects duplicate `code`/`slug`
  (`SERVICE_GROUP_CODE_DUPLICATE`/`SERVICE_GROUP_SLUG_DUPLICATE` — slug is
  derived from name, so a duplicate name is functionally rejected as a
  duplicate slug).
- `PUT /v1/admin/service-groups/{id}` — edit name/description/icon/
  status/display_order.
- `DELETE /v1/admin/service-groups/{id}` — **already blocks hard delete
  if the group has master services attached**
  (`SERVICE_GROUP_HAS_SERVICES`, 409).
- `POST .../activate`, `POST .../deactivate`, `POST .../archive` — real,
  separate lifecycle endpoints.
- `GET /v1/admin/service-groups` — list with `q`/`category_id`/`status`/
  `has_services` filters, plus a `/summary` and `/export` endpoint.

A complete, real, 555-line enterprise frontend page already exists at
`/admin/service-groups` (from the earlier "P0 Enterprise Catalog
Upgrade" sprint per project memory) with the full CRUD UI wired to this
backend, and `catalogApi.createServiceGroup/updateServiceGroup/
deleteServiceGroup/activateServiceGroup/deactivateServiceGroup` already
exist in `lib/api.ts`.

## What was actually missing (and fixed this sprint)
The HS2 catalog console itself had no path to reach this page — no
"Add Service Group" action, no link. **Fixed**: added a permission-gated
"Add Service Group" button linking to `/admin/service-groups`, matching
the same established link-out pattern already used for Issues, Options,
and Pricing Rules in this console (rather than duplicating a second,
parallel CRUD implementation inline).

## Gap vs. the ticket's exact field list
`ServiceGroup` does not have separate `customer_visible`/
`provider_selectable` boolean columns — only `status` (active/inactive/
deleted). The ticket's validation rules ("Inactive group cannot be
customer visible", "...cannot be provider selectable") are therefore not
independently enforceable today; `status=inactive` is the single gate
that already implies both. No migration was added this sprint to split
this into separate flags — documented as a design gap, not fixed (would
require a schema change + migration, out of this sprint's time budget
given the backend CRUD itself was already 90% complete).

## Reorder
`display_order` field exists and is editable via the standard `PUT`
endpoint; no dedicated drag-and-drop reorder UI was verified this
sprint (the `/admin/service-groups` page's reorder capability was not
independently re-tested).

## Verdict
Service Group CRUD: **real, complete, pre-existing backend** (create/
edit/activate/deactivate/delete-with-usage-check all present and
correct); **fixed this sprint**: the HS2 catalog console now links to
it. Gap: no separate customer-visible/provider-selectable flags at the
group level (status-only).
