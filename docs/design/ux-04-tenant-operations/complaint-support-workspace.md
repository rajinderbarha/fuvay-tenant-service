# Complaint / Support Case Workspace (type built, showcase route DEFERRED)

Type: `ComplaintDetailView` (`lib/ux04/types.ts`) — wraps UX-03's
`ComplaintFixture`, adds `customerStatement`, `relatedEntity`
(`EntityLinkView`), `evidence` (`MediaAssetFixture[]`), `timeline` (with
per-entry `customerVisible` flag), `internalNotes: string[]`,
`assignedStaffId`.

No tenant dispute-resolution authority is modeled — there is no field or
method anywhere that lets a tenant "resolve" a case unilaterally or issue
a service credit; `complaint.providerCanRespond` (inherited from the UX-03
fixture) is the only tenant-side authority signal. No showcase route was
built this pass.
