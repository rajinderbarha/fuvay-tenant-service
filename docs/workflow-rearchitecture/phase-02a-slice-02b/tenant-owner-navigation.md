# Tenant-Owner Navigation — Slice 2B

## Scope this slice
Verification only, per the narrow-closure framing — no shell rebuild (already deferred in Slice 2 as page-consolidation-scale work, unchanged this slice).

## Verified
- **No platform-admin pages exposed**: `TenantLayout.tsx`'s nav config contains no `/admin/*` routes.
- **No dead brand routes exposed**: re-confirmed from Slice 2 (frontend only ever calls `/v1/admin/brands`, the canonical route).
- **No deprecated/blocked booking workflow exposed**: re-confirmed — the mobile app's `match-and-price`-only usage and the absence of any `match-providers`/`select-provider` calls remain unchanged.
- **Parts approval and Mark Installed remain contextual**: unchanged from Slice 1/2 — still only reachable from `/(tenant)/service-jobs/[id]/execution`, still gated to `business_approved`/`customer_approved` status for the install button.
- **No global Parts navigation item exists** — confirmed, matches the approved matrix.
- **Package/credit/security-deposit pages** remain under the existing Finance area — not relocated (relocation into a unified "Credits" group is part of the deferred full shell remap).
- **No duplicate menu entries** — reconfirmed, same finding as Slice 2 (the duplicate pages `/provider/reviews`, `/provider/marketing`, `/provider/chat` still have zero nav entries).
- **No fake tenant-owner My Work** — correctly does not exist; no tenant-owner My Work nav item, badge, or page was added, since no tenant-owner aggregation endpoint exists. This is the correct behavior per the explicit instruction ("do not display an empty queue pretending the feature is complete") — the honest state is "not present at all," not "present but always empty."

## Real addition this slice
**Breadcrumb context for the `/service-jobs/[id]/execution` page** (see `breadcrumb-reconciliation.md`) — this page is reached via tenant-owner navigation (Jobs → a specific job → Inspection and Quote), and previously showed a generic, entity-less "Jobs > Service Jobs" breadcrumb regardless of which job was open. Now shows the real job number and the correct workspace step name.

## Not done this slice (deferred, unchanged from Slice 2)
Full remap to the approved 9-item grouping (Home, My Work, Jobs, Services, Team, Customers, Business, Credits, Settings) — the shell still uses its pre-existing 8-group structure. See `deferred-items.md`.
