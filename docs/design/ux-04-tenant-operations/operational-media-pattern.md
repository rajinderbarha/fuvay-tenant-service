# Operational Media Pattern

`JobDetailView.media: MediaAssetFixture[]` reuses UX-03's
`MediaAssetFixture` type unchanged (`previewToken` stands in for whatever
safe reference a real API returns — no storage keys, buckets, or signed
URLs are ever modeled). No dedicated `EvidenceGallery` component or media
showcase route was built this pass; `jobDetailFixture.media` is an empty
array in the current fixture (no photos attached to the sample job), so
the Job Detail Workspace route doesn't currently render a media section
at all. This is a real gap: the type is ready, the component and section
markup are not built.
