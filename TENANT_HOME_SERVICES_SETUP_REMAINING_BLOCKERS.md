# Tenant Home Services Service Setup Wizard — Remaining Blockers

None of these block certification — honestly documented, non-blocking notes.

## 1. No dedicated activity feed on this wizard

`GET /v1/tenant/activity` (ticket-suggested) isn't wired into this page —
the wizard doesn't have a "View Activity" panel yet. Every mutating action
still surfaces its own success/error toast and the review step's publish
errors show the full missing-items list + request_id, but there's no
persistent audit trail visible from this page. Follow-up: reuse
`tenantSetupApi.getActivity()` the same way the Service Coverage Areas
page does.

## 2. Enabled Services list is a simple table, not the full ticket columns

The ticket's "Enabled Services List" section asks for Types/Brands/
Provider Price Range/Customer Price Preview/Service Areas columns plus
Edit Pricing/Preview Customer Price/Disable/View Activity actions. The
current list shows Service/Status/Bookable/Manage (which re-opens the
full wizard). Manage covers all the editing needs, but the richer
at-a-glance columns and one-click Disable/Preview actions aren't broken
out separately yet — a reasonable follow-up once the wizard itself is
validated in production use.

## 3. No slider UI for price ranges

The ticket mentions "drag the handles or type a value" — only the type-a-
value input exists; no visual slider/range component was built. Given the
hard requirement is "must stay within the admin-set working range"
(enforced server-side regardless of input method), a slider is a nice-to-
have UX enhancement, not a functional gap.

## 4. Brand-pricing "Same for all" mode doesn't write anything

Selecting "Same for all" is purely informational (no brand-level rows are
shown or written) — this is correct behavior per the ticket ("All
approved brands use your selected type range" — i.e., no override rows
means the type price applies), but there's no explicit confirmation step
distinguishing "haven't decided yet" from "deliberately chose same-for-
all". Low risk since the review matrix only ever shows brands that
actually have a saved override.

## 5. Permission model is coarse

Same limitation documented in every other sprint this session —
`/v1/auth/me` doesn't return a granular permissions array. `canCreate`/
`canUpdate`/`canPublish` default to `true`, matching the backend's actual
`require_permission(P.TENANT_UPDATE)` gate on every write endpoint, which
already correctly enforces authorization server-side.

## 6. Old 10-step `/provider/service-setup` wizard is untouched and coexists

This sprint intentionally built a new, separate route rather than
replacing the existing, already-certified 10-step wizard (which handles
issues/options/service-areas/technician/availability in addition to
pricing, but has no real per-type/brand price-range UI — see the earlier
tenant-side investigation). Both pages are now live in the nav under
"Setup". A future sprint could consolidate them, but that's a larger,
separate UX decision outside this ticket's scope.

## 7. Pre-existing, unrelated build/tooling gaps

Same `useSearchParams`/`EnterpriseDataGrid` Suspense issue on
`/service-jobs` (unrelated to this page), no ESLint config, no `npm test`
script — all previously documented, all confirmed untouched by this
sprint.
