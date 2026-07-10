# Tenant Service Coverage Areas — Remaining Blockers

None of these block certification — honestly documented, non-blocking notes.

## 1. Zone/Tier resolution is a small heuristic table, not a full postal database

`PINCODE_PREFIX_LOOKUP` in `app/engines/serviceability/constants.py` covers
11 major-city pincode prefixes (including `141` → Ludhiana/Punjab/Tier 2,
matching the ticket's example exactly). Any pincode outside this table
resolves to Tier 2 with the submitted city/state echoed back unchanged,
rather than a real nationwide postal/geo lookup. Building a full India
pincode database is out of this ticket's scope; documented rather than
silently faked for every pincode.

## 2. Plan-based service-area limit is new and only distinguishes 3 plan tiers

`max_service_areas` was added to `PLAN_LIMITS` this sprint (starter=5,
growth=20, enterprise=100) and to the `tenant_limits` table via migration
117. There is no per-tenant override mechanism (e.g. an admin manually
raising one tenant's limit above their plan default) — that would require
a separate admin endpoint, out of scope here.

## 3. "Coverage Rules" is a card on the Service Areas page, not a separate page

The sidebar's new "Coverage" group has two items: "Service Areas" (this
page) and "Service Coverage" (the pre-existing types/brands/issue-types
config page). There is no dedicated "Coverage Rules" backend engine or
page — the 3 coverage rules the ticket describes (primary required, max
areas, active-areas-visible) are shown as a card on this same page instead
of a separate route, since fabricating a second page with no distinct
backend data behind it would just be a UI shell.

## 4. Set Primary / Delete / Toggle do not yet check granular permissions client-side

Same limitation documented in the Business Profile and My Offerings/My
Status sprints — `/v1/auth/me` doesn't return a granular permissions array
to this frontend. `canCreate`/`canUpdate`/`canDelete`/`canSetPrimary`
default to `true` for any authenticated tenant user, matching the
backend's actual `require_permission(P.TENANT_SERVICE_AREA_*)` gate (which
already correctly rejects unauthorized roles server-side) rather than a
finer client-side check that doesn't exist yet.

## 5. Validation Preview failure is non-blocking by design

If the `/v1/tenant/service-areas/validate` call fails (network error,
etc.), the Add Service Area form does not block manual submission — the
create endpoint still runs its own real validation server-side. This
matches the ticket's instruction that section-level errors should not
blank the whole page/flow.

## 6. Pre-existing, unrelated build/tooling gaps

Same `useSearchParams`/`EnterpriseDataGrid` Suspense issue on
`/service-jobs` (unrelated to this page), no ESLint config, no `npm test`
script — all previously documented, all confirmed untouched by this
sprint.
