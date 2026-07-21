# Visual Browser Evidence — UX-06 Round 4

Real Playwright browser session (Chromium headless, 390px viewport, Expo web
dev server on the CORS-allowlisted port 19006, live backend). All screenshots
in `round3-runtime-evidence/` (kept in the same folder as Round 3's for a
single evidence trail; `r4-*` prefix marks this round's captures).

| File | Screen |
|---|---|
| `r4-01-login.png` | Login |
| `r4-02-home.png` | Customer Home (post real login) |
| `r4-03-bookings.png` | Bookings tab |
| `r4-04-profile.png` | Profile tab |
| `r4-05-chat-tab.png` | Chat entry |
| `r4-06-chat-session.png` | Real AI session started |
| `r4-07-language-selector.png` | Searchable language selector (chat-scoped) |
| `r4-08-categories.png` | Real categories (14, from `GET /v1/customer/categories`) |
| `r4-09-offerings.png` | Real offerings for the selected canonical category |
| `r4-10-issue-form.png` | Issue/address collection |
| `r4-11-serviceability-price.png` | **NEW this round**: real `serviceable: true` + real `₹82` price, both live from the seeded Ludhiana coverage |
| `r4-12-after-confirm-attempt.png` | Confirm attempt — shows the real backend rejection (not a fixture success screen) |

No screenshot shows fabricated data: every value visible (categories, prices,
serviceability text) traces to a specific real API response documented in
serviceability-live-evidence.md / price-live-evidence.md.

**Not visually verified this round** (see production-design-route-audit.csv):
Notifications, Booking Detail, standalone Service Detail (doesn't exist as a
separate screen). These are explicit gaps, not silently assumed clean.
