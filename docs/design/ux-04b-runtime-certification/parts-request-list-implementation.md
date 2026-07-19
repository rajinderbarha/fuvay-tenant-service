# Parts Request List Implementation

- Type: `PartsRequestListItemView` (`lib/ux04/types.ts`) — extends the
  shared `PartsRequestFixture` with list-only presentation fields
  (`technicianName`, `serviceJobLabel`, `installationState`,
  `lastActivityAt`), never a separate PartsRequest model.
- Component: `components/ux04/PartsRequestList.tsx` — client-side
  search + status filter over the fixture list; renders loading/empty/
  error states explicitly via props, not inferred.
- Fixtures: `partsRequestListFixture` (3 rows, 3 different statuses:
  requested/approved/rejected) and `partsRequestListEmptyFixture`
  (`lib/ux04/fixtures.ts`).
- Route: `/dev/ux-04/parts-list` — a state switcher (multi/empty/loading/
  error) exercises all 4 states through the one real component, not 4
  separate mock pages.
- Test: `components/ux04/__tests__/PartsRequestList.test.tsx` — 7 tests:
  multi-row render, empty state, loading state, error state (no raw
  exception string), search filter, status filter, and a negative
  assertion that no `fo_job_*` (field_ops.Job) id or install-control
  button ever renders.
