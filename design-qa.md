**Comparison target**

- Source visual truth: `C:\Users\Aiviq Technologies\.codex\generated_images\019ff122-d815-7d43-89db-6975b88031ff\exec-62b65702-51e5-427e-94b4-465b39da7a63.png`
- Implementation screenshot: `C:\Users\Aiviq Technologies\AppData\Local\Temp\fuvay-home-resume.png`
- Combined comparison evidence: `C:\Users\Aiviq Technologies\AppData\Local\Temp\fuvay-design-comparison-resume.png`
- App-wide comparison evidence: `C:\Users\AIVIQT~1\AppData\Local\Temp\fuvay-app-wide-qa.png` (selected direction, Home, Bookings, Assistant, Support, Profile, Notifications, and Saved Addresses in one same-density contact sheet)
- Extended native-screen evidence: `C:\Users\Aiviq Technologies\AppData\Local\Temp\fuvay-home-below.png`, `fuvay-home-deep.png`, `fuvay-home-deep2.png`, and `fuvay-home-end.png`
- Viewport and density: Android native viewport at 426 x 960 dp, captured at 2x as 852 x 1920 pixels. Source and implementation were compared at the same 852 x 1920 pixel density. The combined evidence is 1704 x 1920 pixels.
- State: authenticated customer, PIN 140412, serviceable Home Services catalog, live marketing campaign, active bookings, light theme.

**Findings**

- No actionable P0, P1, or P2 visual mismatch remains in the selected first viewport.
- Fonts and typography: hierarchy, weights, line heights, wrapping, and compact labels match the source's marketplace density. The real campaign title wraps at the same visual level as the reference.
- Spacing and layout rhythm: header, 44 dp search control, 228 dp hero, section gaps, card radii, recommendation rail, and raised Assistant tab are aligned to the selected direction. Persistent navigation remains visible without covering content.
- Colors and visual tokens: the blue Fuvay palette, pale blue canvas, white surfaces, green live-booking status, and campaign scrim map consistently to the native design tokens.
- Image quality and asset fidelity: the supplied Fuvay logo is used as a real raster asset; campaign and recommendation imagery comes from live HTTPS/Cloudinary URLs. There are no placeholder images, handcrafted SVGs, or code-drawn visible assets.
- Copy and content: intentional live-data substitutions are accepted. The implementation shows the customer's real PIN, actual configured service groups, actual booking state, and live campaign offer instead of the mock's invented locality, ETA, technician, service inventory, and discount amount.
- Below-fold extension: the mock did not define these states. Native captures confirm clean layout for common problems, additional active bookings, repair/consultation partitions, booking capabilities, process guidance, assurances, location, and support. Each section is backed by live aggregate data or by a documented platform capability and hides when its source is empty.
- App-wide consistency: the primary tabs and sampled inner routes use the same blue semantic tokens, pale canvas, white card surfaces, 16 dp card radius, 48 dp actions, typography hierarchy, Ionicons set, and safe-area behavior. No secondary route falls back to the removed customer web surface or old orange customer branding.
- Cross-tab workflow: a PIN chosen on Home is now a single persisted native preference shared above the tab navigator. Direct Assistant entry uses that selection immediately; physical Android evidence confirms it opens the real category chooser instead of the incorrect location-empty state.
- Notification truthfulness: unread lists no longer end with the contradictory “You’re all caught up” label. Quote notifications now carry an allowlisted booking destination and open the real Booking Details estimate-approval section; historical live rows were backfilled through migrations 306–307.

**Focused comparison evidence**

- A separate crop was not required: at 852 x 1920 the combined full-view comparison keeps the logo, search, campaign typography, service icon, booking card, recommendation imagery, and bottom navigation readable at native density.

**Comparison history**

1. Earlier pass: search height and hero proportions were too large, campaign copy crowded the image, and the date/action row could collide with the hero body.
2. Fixes: search reduced to 44 dp; hero fixed to 228 dp with clipping; typography reduced to 26/29 and 17/21; nonessential hero subtitle removed; date and CTA anchored to the bottom; recommendation copy and card heights compacted.
3. Post-fix evidence: `fuvay-design-comparison-resume.png` shows the corrected same-viewport source and implementation together. No P0/P1/P2 issue remains.

**Primary interactions tested**

- Change service location.
- Search live catalog data.
- Open Ask Fuvay from search and the Home prompt.
- Open a service group through its real category.
- Record campaign delivery and click events.
- Open an active booking.
- Open a preselected live issue without duplicating it across Home sections.
- Navigate to all bookings and Support.
- Open the center Assistant tab directly after selecting a browsing PIN on Home.
- Open Notifications, filter unread items, and follow a quote notification into Booking Details.
- Open Profile, Saved Addresses, and Add Address while preserving the same native shell.
- Pull to refresh and render loading, API error, offline, missing-address, and unserviceable states.

**Follow-up polish**

- P3: replace the dark logo lockup with a transparent light-background brand export if the brand team supplies one. The provided SVG uses white lettering and therefore requires a dark backing in the current light header.

final result: passed

## Native Home — selected editorial option 2 — 2026-08-23

**Scope and target**

- Exact selected source: `C:\Users\Aiviq Technologies\.codex\generated_images\019ff122-d815-7d43-89db-6975b88031ff\exec-220fc080-c189-4ce0-8ff1-a163ee83c176.png`.
- Light emulator capture: `C:\Users\Aiviq Technologies\AppData\Local\Temp\fuvay-option2-light-final-pass.jpg`.
- Dark emulator capture: `C:\Users\Aiviq Technologies\AppData\Local\Temp\fuvay-option2-dark-final-pass.jpg`.
- Combined comparison evidence: `G:\serviceos\mobile\customer-app\design-option2-comparison.jpg`.
- Runtime: native Android/Expo app at 1080 x 2340 px. The paired source mock uses a compressed concept-board viewport, so the implementation preserves its hierarchy and proportions responsively rather than distorting the real phone viewport.

**Blocking comparison result**

- P0: none. Home loads with real API data; the campaign, local catalog entry, booking, recommendation, nationwide Digital Studio lead path, theme switch and tab navigation remain interactive.
- P1: none. Light and dark shells both reproduce the source's neutral editorial direction, image-led hierarchy, serif campaign display type, compact location/search header, live-booking rail, media recommendations and neutral elevated assistant action.
- P2: none. Media text no longer inherits the dark theme's inverse-on-light token; it remains readable over arbitrary campaign artwork in both modes. The shell is warm porcelain in light mode and ink/graphite in dark mode without blue-tinted permanent surfaces.
- Live-data exception: only one service group is currently bookable for PIN 140412, so the rail truthfully shows AC & HVAC instead of fabricating the four services present in the visual concept.
- Functional extension: compact capability chips beneath the Digital Studio banner expose every live nationwide service. They intentionally extend the reference because the project has six independently actionable global offerings backed by the API.

**Interaction and regression evidence**

- Native emulator: switched Light -> Profile -> Dark -> Home and confirmed theme persistence, safe-area behavior, scroll restoration and the neutral bottom navigation treatment.
- Focused native tests: 2 suites / 11 tests passed for Home and CustomerTabs.
- Backend global-services workflow: 3 tests passed.
- TypeScript: `tsc --noEmit` passed.

**Remaining P3 polish**

- The source concept includes four service-photo cards. As more service groups become genuinely enabled for the selected PIN, the existing horizontal rail will populate them automatically with the same media-card treatment.

final result: passed

## Native My Bookings and Ask Fuvay redesign — 2026-08-23

**Scope**

- Native customer app only: My Bookings list and the Ask Fuvay booking-assistant chooser/conversation.
- Existing API routes, server-side booking filters, pagination, support navigation, assistant session, bootstrap, issue selection, question flow, and booking confirmation were retained.

**Visual evidence**

- My Bookings final: `C:\Users\Aiviq Technologies\AppData\Local\Temp\fuvay-bookings-final3.png`
- Ask Fuvay live issue selection: `C:\Users\Aiviq Technologies\AppData\Local\Temp\fuvay-current.png`
- Ask Fuvay first live question: `C:\Users\Aiviq Technologies\AppData\Local\Temp\fuvay-assistant-question.png`
- Viewport: Android native 426 x 960 dp, captured at 852 x 1920 pixels.

**Outcome**

- My Bookings now uses a scan-first hierarchy: authoritative totals, filter tabs, freshness state, urgency groups, compact operational cards, next-step guidance, progress, human-readable schedules, pricing, and clear detail/support actions.
- Ask Fuvay now uses the same Fuvay-blue design language: service chooser hero, location context, live category cards, assurance strip, conversation header, and a clean four-stage booking tracker.
- Physical native testing exposed and fixed a production contract mismatch: the backend may correctly return `null` for pending draft readiness states. The app now accepts those values and advances from category selection into the real issue and question flow.
- Final physical flow confirmed Home Services -> live issue list -> "AC is not cooling" -> live "What type of AC is it?" question and supported options.

**Verification**

- TypeScript: passed (`tsc --noEmit`).
- Full native customer-app suite: 147 suites and 1,218 tests passed.
- Contract regression: pending nullable draft-readiness states covered.
- Source hygiene: scoped `git diff --check` passed; only existing line-ending notices remain.

final result: passed
