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

## Customer design system — Circle Tile + Customer Home v2 — 2026-08-30

**Source of truth**

- Component language: `C:\Users\Aiviq Technologies\Downloads\Circle Tile Light + Dark.dc.html`.
- Latest Home hierarchy: `C:\Users\Aiviq Technologies\Downloads\Customer Home Screen v2.dc.html`.
- Rendered reference evidence: `G:\serviceos\.artifacts\customer-design-system\customer-home-v2-reference.png`.
- The reference's amber accent was intentionally mapped to the existing Fuvay brand and semantic palette; its neutral depth, spacing, tile construction, and light/dark behavior were retained.

**Implemented system**

- One `AppSurface` contract now owns raised, interactive, inset, and flat material treatments.
- One `AppIconTile` contract now owns circular and squircle Lucide service/action tiles with semantic tones.
- One `AppLucideIcon` registry now supplies navigation, home-service, search, status, and action icons.
- Cards, buttons, icon buttons, inputs, badges, screens, and bottom navigation consume the shared material recipes instead of screen-local shadows and backgrounds.
- Home now follows the v2 information hierarchy: identity/location row, home-care command title, next visit summary, microphone search, layered service tiles, neutral live-booking timeline, and individually elevated recommendation cards.
- Admin-provided section order, visibility, layout variants, campaigns, services, bookings, and action routes remain intact.

**Blocking comparison result**

- P0: none. Strict TypeScript and the Home/API fixture suite pass; backend-driven content and navigation contracts remain intact.
- P1: none in the implemented component hierarchy. Fixed the previous one-off purple booking surface and nested recommendation panel that conflicted with the v2 system.
- P2: Android emulator screenshot automation was unavailable because the emulator's Android `system` process raised its own ANR dialog after a cold restart. Expo Go remained the resumed activity and logcat showed no React Native fatal or bundle-resolution error, but no post-change native screenshot is claimed from that device state.
- P3: when the emulator system image is healthy, capture one light and one dark authenticated Home screenshot for the visual archive; this is evidence follow-up, not a code-contract gap.

**Verification**

- TypeScript: passed (`tsc --noEmit --incremental false --skipLibCheck`).
- Focused ESLint: passed for Home, navigation, surfaces, tiles, and Lucide registry.
- Jest: 5 suites / 20 tests passed, including Home, theme material recipes, AppSurface consumers, and AppIconTile.
- Source hygiene: scoped `git diff --check` passed; only repository line-ending notices remain.
- Runtime: API healthy on port 8000, Metro healthy on port 8081, and Expo Go resumed the customer experience without React Native fatal errors.

final result: passed

## Native customer Home — Home (4) parity and Lucide polish — 2026-08-28

**Comparison target**

- Source visual truth: `C:\Users\Aiviq Technologies\Downloads\Home (4).png`.
- Final dark first viewport: `G:\serviceos\.artifacts\customer-home\home-dark-final-top2.png`.
- Final dark lower-section evidence: `G:\serviceos\.artifacts\customer-home\home-dark-final-mid.png`.
- Final light first viewport: `G:\serviceos\.artifacts\customer-home\home-light-final.png`.
- Runtime: authenticated native Android customer app in Expo Go at 1080 x 2340 px, tested with the real PIN 140412 Home aggregate.

| Area | Result | Evidence |
| --- | --- | --- |
| Header and search | Passed | Compact greeting/location hierarchy, 40 dp visual action circles inside accessible targets, neutral tokenized search field, and no duplicated assistant control inside search. |
| Hero slider | Passed | Backend-managed multi-slide hero keeps the approved image-led marketplace treatment; broken/expired media falls back to packaged campaign art instead of a blank block. |
| Popular/nearby services | Passed | Four-column responsive grid uses the requested bright, two-dimensional Lucide line icons and solid semantic wells in both themes. |
| Recommendations | Passed | Editorial lead plus a stable two-column supporting grid; cards are unique live master-service records and collapse cleanly when fewer results exist. |
| Global and spotlight sections | Passed | Backend-driven section order/content retained; Fuvay global services use the same colored Lucide system and Spotlight no longer duplicates a campaign to fill an empty slot. |
| Spacing and responsiveness | Passed | Shared screen, section, card, row and inline tokens govern rhythm; Android fractional-width tolerance prevents one-column wrapping on wider phones and compact tablets. |
| Light theme | Passed | Neutral pale canvas, white elevated surfaces, readable dark text, colored icon wells, and image-first cards confirmed on device. |
| Dark theme | Passed | Approved charcoal canvas and layered graphite surfaces, high-contrast text, saturated icon wells, campaign imagery, and persistent navigation confirmed on device. |
| Data integrity | Passed | PIN, catalog groups, master services, campaigns and availability remain API-backed; no fake services or duplicate fallback records are rendered. |

**Automated verification**

- Customer app TypeScript: passed (`npx tsc --noEmit --pretty false`).
- Focused Home lint: passed (`HomeScreen.tsx` and `HomeLucideIcon.tsx`).
- Native Home/API/component tests: 8 suites, 60 tests passed.
- Jest now transforms `lucide-react-native` ESM modules, so CI exercises the same per-icon imports used by Metro.

**Accepted live-data differences**

- The reference contains illustrative services and booking content. The implementation truthfully renders the services, campaigns and bookings returned for PIN 140412, so counts and titles may differ while the selected layout and component behavior remain the same.
- Campaign art and ordering remain admin-controlled; the screenshot may show a different valid slider frame after the six-second rotation.

final result: passed

## Admin command-center header and KPI unification — 2026-08-27

**Comparison target**

- Source visual truth: the dark command-center screenshot supplied in this conversation, showing the compact eyebrow/context header, right-aligned actions, operational strip, tabs, and a five-card KPI row.
- Implementation route: `http://localhost:3000/admin/dashboard`.
- Target state: authenticated super admin, dark theme, Home Services overview.
- Target viewport: approximately 1467 x 414 pixels based on the supplied source.

**Implemented**

- `PageHeader` is the single shared page-heading implementation. The dashboard, settings, intelligence, security, and threat-investigation headers now compose it instead of maintaining local hero markup.
- `SummaryCard` is the single operational KPI tile. The legacy `MetricCard`/`StatCard` name is a compatibility adapter that renders `SummaryCard`; it no longer owns separate markup or styling.
- Header rhythm, page rhythm, action gaps, KPI gaps, card padding, and responsive admin-shell padding now consume the common `--space-*` scale through semantic `--layout-*` tokens.
- Admin-only eyebrow wording is explicit at admin call sites. The shared component no longer injects “Fuvay administration” into tenant pages.
- The architecture guard rejects feature-local implementations of the canonical header, KPI, card, button, form, pagination, empty-state, and action-menu primitives.

**Automated verification**

- Super-admin TypeScript: passed (`npx tsc --noEmit`).
- Tenant portal TypeScript against the changed shared package: passed (`npx tsc --noEmit`).
- Super-admin Vitest suite: 2 files, 4 tests passed.
- Super-admin production build: passed; all 141 routes generated.

**Visual verification status**

- The in-app Browser runtime reported that no browser instance was available, so a same-viewport implementation screenshot and combined visual comparison could not be captured in this run.
- No claim of pixel-level visual parity is made without that evidence. Automated and structural validation are complete; browser-rendered visual comparison remains blocked by the unavailable Browser runtime.

final result: blocked

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
