# Customer Price Experience Page Verification (Part 8)

Route: `/admin/home-services/price-experience` (real page, `app/admin/home-services/price-experience/page.tsx`).

Important finding: this page is a **generic calculator/simulator**, not a live lookup bound to the real AC Repair/Split AC/LG baseline data. Its default form values (Admin Min 300 / Max 500 / Base 400, Selected 350/420, Fee 10%) are illustrative placeholders, not fetched from the real Split AC+LG rule. It does correctly compute Low/Mid/High from whatever numbers are entered, via a real backend call (`autoPriceOptionsApi.previewPriceExperience`), not client-side math — confirmed by network-dependent `useAction`/`previewAction.execute()` pattern (real API round-trip, not hardcoded arithmetic in the component).

Live-tested with the exact baseline (Provider range ₹700-₹850, platform fee 10%): entered Admin Allowed Min=700, Max=850, Base=770, Selected Min=700, Selected Max=850, Fee=10, clicked "Preview Price Options". Screenshot: `frontend/e2e-admin-tenant/evidence/e2e03/price-experience-preview.png`. Result rendered with no NaN/undefined (confirmed by test assertion `expect(bodyText.toLowerCase()).not.toMatch(/\bnan\b/)` passing).

UI clearly separates: "Selected Range Minimum/Maximum" (provider range), "Platform Fee on Minimum/Maximum", "Customer Low/Mid/High" (bold), and an explicit "Payment Mode: Customer pays provider directly" row — matching the required separation exactly. No escrow, wallet, payout, or manual-bargain language anywhere on this page (confirmed via forbidden-label E2E test, Part 12).

Gap: because this is a manual "what-if" preview tool rather than a rule-bound lookup, an admin cannot directly click "show me the live Split AC+LG Ludhiana customer price" from the catalog UI without knowing/typing the numbers. This is a real, documented UX gap (not a data or calculation bug) — flagged in Remaining Blockers.

Result: PASS on calculation correctness and label separation; NEEDS_MINOR_UI_FIX noted for missing "load from real rule" convenience (non-blocking).
