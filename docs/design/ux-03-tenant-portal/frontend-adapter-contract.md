# Frontend Adapter Contract

`Ux03DataAdapter` (in `lib/ux03/types.ts`) declares one async method per
entity list/get operation. `ux03FixtureAdapter` (in `fixtures.ts`) is the
only implementation this phase — entirely fixture-backed. Swapping to a
real API means implementing the same interface against `lib/api.ts`
(tenant-portal's existing API client) without changing any consuming
component, since components only ever depend on the `Ux03DataAdapter`
shape, not the fixture module directly (aside from the dev showcase pages,
which import fixtures directly for simplicity and are explicitly dev-only).
