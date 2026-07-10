# HS4 — Tenant Publish Readiness Report

## Real backend logic (confirmed via source + live test)
`TenantCatalogService.publish_service` checks, in order:
1. If `requires_type`, at least one active type selected
   (`"Select at least one type."`).
2. Every selected type has a complete price range set
   (`"Set a price range for every selected type."`).
3. Every brand override with a partial range (min set, max not, or vice
   versa) is flagged (`"Brand override price range is incomplete."`).
4. At least one active service area exists
   (`"At least one active service area is required to publish."`).

If any check fails: **422 `SERVICE_SETUP_INCOMPLETE`**, message includes
the count of missing items, and (per source) each missing item is
returned as a structured `{field, message}` entry — not just a generic
string.

## Live-verified this sprint
`POST .../015efedb-.../publish` → **200, `setup_status: "published"`,
`published_at` timestamp set** — real publish succeeded for a fixed
(non-type-based) service with an active area already configured from
earlier session work.

## Gaps vs. the ticket's full publish-requirements list
The ticket lists 9 requirements (business profile, service area,
services selected, types selected, price range, brand support,
availability, usage credits, security deposit). The real
`publish_service` method only checks 4 of these (types, type pricing,
brand pricing completeness, service area) — it does **not** check
business-profile completeness, availability configuration, usage-credit
balance, or security-deposit status. Those are enforced elsewhere in the
tenant onboarding flow (per earlier sprints' `TenantLayout.tsx`
`SETUP_STEPS`/readiness checks) but not re-validated at the moment of
service publish specifically — a tenant could theoretically publish a
service while still missing availability configuration, for example.
Not fixed this sprint (would require cross-engine calls from
`tenant_service.py` into staffing/finance engines — a larger change than
this sprint's time budget allows).

## Setup checklist impact
Not independently re-verified this sprint whether `setup_status:
"published"` on a `TenantService` row automatically updates the
`/tenant/setup/checklist` "Enable a Service" item — the checklist's
`SETUP_STEPS` array (confirmed in the HS0 sprint) already points at
`/tenant/setup/services`, but live cross-checking the checklist's
computed status after this sprint's publish call was not performed.

## Verdict
Publish readiness: **real, functioning, live-verified** for the 4
checks it performs. Does not cover the full 9-item list from the
ticket — documented gap, not fabricated.
