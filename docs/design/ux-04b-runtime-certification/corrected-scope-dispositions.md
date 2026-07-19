# Corrected Scope Dispositions

Two UX-04A dispositions were wrong and are corrected in
`original-27-item-reconciliation.csv`:

- **Item 6, field_ops.Job detail**: was `NOT_APPLICABLE_WITH_REPOSITORY_EVIDENCE`.
  The reasoning ("no model-specific sections exist beyond Booking Detail")
  was true for the *ServiceJob-only sections* but wrong as a reason to skip
  building the page entirely — a field_ops.Job detail view showing its own
  real fields (status/SLA/timeline/notes/activity/audit) distinct from the
  pre-transition Booking Detail view is a valid, buildable page. Corrected
  to **IMPLEMENTED** — see `field-ops-job-detail-implementation.md`.
- **Item 14, Parts Request list**: was `NOT_APPLICABLE_WITH_REPOSITORY_EVIDENCE`,
  reasoned from "the fixture data only has one row" — not valid exclusion
  evidence (fixtures are ours to write; a real list view doesn't require
  pre-existing multi-row data, it requires building the list UI + writing
  a realistic fixture set). Corrected to **IMPLEMENTED** — see
  `parts-request-list-implementation.md`.

## Item 21 (Compliance submission) — re-verified against actual UX-03 source

Read `frontend/tenant-portal/app/dev/ux-03/compliance/page.tsx` directly
this pass (not just trusting the earlier doc claim). Confirmed: it is a
real, rendering 16-line page — imports `FIXTURE_COMPLIANCE` from
`lib/ux03/fixtures.ts`, maps each item to a design-system `Card` showing
`c.requirement` as the title, `c.status` via `StatusBadge`, and each
`c.history` entry's timestamp/actor/action. It does NOT use the
`TenantListPage`/`TenantDetailPage` pattern (uses `Card` directly) —
correcting an inaccurate assumption in this doc's first draft. It is a
genuine working page, not a stub or doc-only claim, but it is simpler
than UX-04's other list/detail patterns (no filters, no detail-drill-down
route, no `affectedFields`/`resubmissionSupported` UI). Disposition
`ALREADY_IMPLEMENTED_AT_BASELINE` confirmed accurate with real source
evidence, with this more precise description of what it actually does.
