# Direct Payments design QA

**Source visual truth**

- User-attached Direct Payments desktop screenshot, 1560 x 853 pixels.
- Matching source artifact: `C:\Users\Aiviq Technologies\Downloads\Provider service pricing flow (2)\Direct Payments.dc.html`.

**Implementation evidence**

- Route: `/home-services/direct-payments`.
- Local implementation source: `app/(tenant)/home-services/direct-payments/page.tsx`.
- Browser-rendered implementation screenshot: unavailable for this uncommitted version. The public URL renders the deployed pre-change build; the local URL redirects to login because its browser origin has no provider session.
- Target viewport: desktop 1560 x 853, device density 1x. Tablet and mobile behavior is covered by explicit 1280px, 1024px and 768px layout breakpoints but has not been visually captured.
- State: populated `Needs action` queue in the reference; automated populated, empty, error, and undeclared-job states in the implementation.

**Full-view comparison evidence**

- The source establishes a full-width queue under six equal KPI cards, a single filter bar, underlined status tabs, compact stacked payment rows, and no permanently open detail pane.
- The implementation now follows that composition. The previous two-column queue/detail split, finance eyebrow and header toolbar were removed. Date/export/refresh controls remain functional in a compact secondary toolbar below the queue.
- A post-change rendered screenshot cannot be captured until the code is deployed or a provider signs into the local origin, so this comparison is not eligible to pass yet.

**Focused region comparison evidence**

- Queue rows were reviewed against the readable source crop: job reference and time are the heading, status sits at the far right, and Customer, Service, Declared, Method, Provider, Customer confirmation and Updated appear as seven scan fields.
- The KPI area uses six equal tracks, compact uppercase labels, right-aligned semantic icons and mono-style numeric values.
- The filter bar exposes labelled search, status, method, service and technician controls; status tabs expose selected state to assistive technology.
- No imagery is present in the source or implementation. Icons use the product's existing Lucide library rather than CSS/SVG substitutes.

**Findings**

- [P1] Post-change visual evidence is unavailable.
  Location: authenticated Direct Payments route.
  Evidence: the public route is still the previous deployment and the local origin has no authenticated provider session.
  Impact: typography, precise spacing, responsive wrapping and final visual parity cannot be signed off from source code or tests alone.
  Fix: deploy the tenant bundle (or authenticate the local origin), capture the same populated state at 1560 x 853, compare it with the reference, and fix any visible P1/P2 drift.
- [P3] Date range, Export and Refresh are retained below the queue although the supplied screenshot does not show them. They preserve existing operational capability without changing the primary visual hierarchy.

**Required fidelity surfaces**

- Fonts and typography: implementation inherits the established tenant Instrument Sans stack and uses the existing mono token for labels/numbers; final optical comparison is blocked on a rendered capture.
- Spacing and layout rhythm: tracks, gutters, card radii and row fields follow the source composition; final pixel comparison is blocked.
- Colors and visual tokens: existing tenant surface, border, accent and semantic tokens are used; no new gradient or decorative color was introduced.
- Image quality and asset fidelity: not applicable; neither screen contains raster imagery.
- Copy and content: title, subtitle, notice, KPI labels, filters, tab labels and row fields match the source. Dynamic amounts and counts remain server-owned.
- Accessibility and interactions: controls have labels, rows are keyboard buttons, active tabs expose `aria-pressed`, the queue exposes busy state, details are a focus-trapped dismissible dialog, and failures remain retryable.

**Comparison history**

- P1 — Two-pane composition: replaced the permanent detail column with a full-width queue and on-demand modal.
- P2 — Header hierarchy: removed the duplicate Finance eyebrow and moved utility actions out of the primary header.
- P2 — Row semantics: replaced the dense table with responsive scan rows and stopped showing expected price as a declared payment.
- P2 — Navigation context: simplified the breadcrumb to Workspace / Direct Payments and kept Finance & Credits selected in the sidebar.

**Implementation checklist**

- [x] Full-width desktop queue.
- [x] Six responsive KPI cards.
- [x] Search and all four live filters.
- [x] URL-addressable status tabs, paging and selection.
- [x] On-demand payment detail and retry state.
- [x] Responsive desktop/tablet/mobile grids.
- [x] Focus and semantic labels.
- [x] Focused automated tests and TypeScript validation.
- [ ] Same-state post-change browser screenshot and visual comparison.

final result: blocked
