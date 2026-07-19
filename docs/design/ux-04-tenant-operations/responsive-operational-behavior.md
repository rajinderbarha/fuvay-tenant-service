# Responsive Operational Behavior

Built UX-04 pages reuse `@serviceos/design-system`'s `PageShell`/`PageHeader`
(flex-wrap layout, no fixed-width containers) — the same responsive
foundation verified in UX-03. Tables in `booking-list` are plain HTML
tables without an explicit horizontal-scroll wrapper; on narrow viewports
this will overflow rather than scroll gracefully — a **known gap**, not
verified against a real mobile viewport this pass (no visual/browser
screenshot check was performed, only source review). `OperationalActionQueue`
and card-style components (`AssignmentCandidateCard`, `QuoteSummary`, etc.)
use flexbox with `flexWrap`/`gap` and should reflow reasonably at narrow
widths, but this was not visually confirmed.
