# Complaint / Support Case Workspace (UX-04A)

New: `components/ux04/ComplaintWorkspace.tsx`, fixture
`complaintDetailFixture`, route `/dev/ux-04/complaints`. Renders case id,
category, status, customer statement, related-entity link, assigned
staff, timeline (internal entries marked distinctly), and
`providerCanRespond`. `ComplaintWorkspace.test.tsx` asserts no
resolve/refund button renders and the internal-only marker appears on the
internal timeline entry.
