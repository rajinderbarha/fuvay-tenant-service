# Home Screen Root-Cause Audit (UX-07 Pass 3d)

Read `mobile/customer-app/src/screens/HomeScreen.tsx` in full at HEAD `8a78724`
before making any change. Findings below are each verified against the
actual pre-change file (line numbers refer to that version), not assumed.

| Brief's hypothesis | Verified against the real file? | Finding |
|---|---|---|
| Oversized greeting banner | Yes | `header` style: `paddingTop:56, paddingBottom:24` on a full-width brand-navy block containing a 22px bold greeting + subtitle + profile circle — the single largest visual element on the screen, present on every visit regardless of content below it. |
| Repeated "Home" title | Partially true | The screen itself has no literal second "Home" heading, but the greeting subtitle ("What do you need help with today?") duplicates the tab bar's already-visible "Home" context with no added information — an IA redundancy, not a literal string duplicate. Corrected framing kept in the redesign notes below. |
| Generic "Customer" fallback greeting | Not present in the code, but the real bug was worse: no fallback path existed at all for a real name — `firstName = user?.full_name?.split(" ")[0] ?? "there"` fell back to "there", not "Customer". The brief's phrasing was a hypothesis to verify, and it was inaccurate as literally stated; the underlying honest-fallback requirement is still real and is what Pass 3d's `firstName ?? null` + omit-name-on-null logic addresses more precisely (never inventing "Customer" OR "there" as a fake name substitute — a time-of-day-only greeting is the honest choice when no real name is loaded). |
| Oversized category cards | Yes | `CARD_W = (width-48)/2` — two per row, each `padding:16` with a 34px emoji, a name line, a full pill row, and a "Tap to start →" cue: 4 stacked content rows per card for what should be a single navigational tap target. |
| Emoji icons | Yes | Every category (`❄️ 🔧 ⚡ 🧹 🪲 🏠 🎨 🪵 💧 🏡`), the bot avatar (`🤖`), and empty-state icon (`📋`) were raw emoji glyphs, inconsistent in weight/style across platforms and never matched to the single icon system (`@expo/vector-icons`, already a real dependency) used elsewhere in the app shell. |
| Premature Repair/Service/Consult badges | Yes | Every category card rendered a `typePills` row (`cat.types.map`) showing all applicable booking-type badges *before* the customer had even chosen the category — a decision that belongs inside the guided flow after category selection, not as a pre-commitment shown 10 times on the landing screen. |
| Missing search | Yes | No search entry point existed anywhere on Home. |
| Missing SmartBot primary CTA | Yes | SmartBot (`DeepSeekChatScreen`, the "AI Assistant" tab) was reachable only via the tab bar, with zero promotion or explanation on Home — a customer landing on Home had no way to discover it was the primary path to describe an issue in their own words. |
| Duplicate Chat + AI-Assistant tabs | Yes, confirmed via `TabNavigator.tsx` | Both "AI Chat" (SmartBot/DeepSeekChatScreen) and "Chat" (human/provider support, `ChatScreen`) occupied separate primary tab slots with near-identical 💬/🤖 iconography and no differentiation visible from the tab bar alone — a real customer-facing ambiguity even though the two screens are backed by genuinely distinct real APIs (see Pass 3b's disposition note, re-confirmed this pass). |
| Wrapping bottom-nav labels | Not literally wrapping (labels were short), but the deeper issue: only 4 real destinations were meaningfully differentiated in 5 slots (Home/Bookings/AI Chat/Chat/Profile) with no Notifications entry point on the tab bar at all, despite a real `notificationsApi` existing in `api.ts`. |

## What Pass 3d changed and why

See `customer-home-information-architecture.md` and
`customer-home-implementation-report.md` for the full rebuild rationale and
diff-level detail. In one line: Home now leads with a real-name-or-honest-
fallback greeting, a search entry and a single SmartBot CTA (the two primary
paths into the guided booking flow), a real active-job status (or a light,
non-dominant empty state), compact single-icon popular-service tiles with
no premature badges, real recent bookings, and a small trust-info row — and
the bottom nav is narrowed to exactly 5 differentiated destinations (Home /
Bookings / SmartBot / Notifications / Profile), with Chat folded into
Profile rather than deleted.
