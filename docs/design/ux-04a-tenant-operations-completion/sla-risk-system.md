# SLA / Risk System (UX-04A)

New: `components/ux04/SLAExplanation.tsx`, fixture `slaGalleryFixture`
(all 9 `SLAState` values with realistic explanations), route
`/dev/ux-04/sla-risk`. `SLAIndicator.test.tsx` (new) asserts every one of
the 9 states renders its distinct label via a loop over the gallery
fixture — this is a stronger guarantee than the baseline's single-state
spot checks.
