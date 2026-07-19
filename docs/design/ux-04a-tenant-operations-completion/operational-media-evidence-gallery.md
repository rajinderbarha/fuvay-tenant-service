# Operational Media / Evidence Gallery (UX-04A)

New: `components/ux04/EvidenceGallery.tsx`, route `/dev/ux-04/media`,
consuming UX-03's `FIXTURE_MEDIA_ASSETS` unchanged. Renders `label`,
`kind`, `sizeLabel`, `uploadedAt`, and a placeholder preview block —
`previewToken` is never rendered as text anywhere in the component.
`EvidenceGallery.test.tsx` asserts the label renders but the raw
`previewToken` string value never appears in the DOM, and that an empty
asset list renders an honest "No media attached" message rather than an
error.
