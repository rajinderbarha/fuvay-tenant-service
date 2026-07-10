# HS7 — Remaining Blockers

1. **No customer-facing frontend.** Neither a web app nor the existing
   `mobile/customer-app` is wired to the real (now-fixed) booking-draft
   API. This is the single largest gap and the primary reason full
   `READY` certification isn't warranted this pass. See
   `HS7_CUSTOMER_BOOKING_UI_REPORT.md`.
2. **No booking cancellation endpoint post-confirmation.** Only
   pre-confirmation draft cancellation (`POST /{draft_id}/cancel`) exists.
   The ticket's `POST /v1/customer/bookings/{booking_id}/cancel` has no
   real backend counterpart.
3. **No rating submission endpoint verified for Home Services bookings.**
   A real Review & Rating Engine exists platform-wide (`/v1/reviews`,
   healthy per `/health`) but wasn't checked against Home Services
   booking IDs specifically this pass.
4. **Systemic `updated_at`-missing-column gap, only partially fixed.**
   4 tables in the direct HS7 call path were fixed (migrations 122-125).
   A broader scan found ~20 more affected tables elsewhere in the
   codebase (coaching/real-estate draft events, various audit/log
   tables) — out of Home-Services scope for this ticket, not fixed,
   documented as a known pre-existing platform issue for a future sprint.
5. **`bargain_rules` table was completely empty** platform-wide before
   this pass (0 rows). One row was seeded for AC Repair/Split AC/LG to
   complete live verification. Every other real service/type/brand
   combination in the catalog likely has the same gap — `match-and-price`
   will fail with `PRICE_OPTIONS_UNAVAILABLE` for any of them until a
   proper admin bargain-configuration pass seeds the rest. This looks
   like a genuine gap in whatever sprint (HS3?) was supposed to deliver
   customer-facing bargain ranges — not something HS7 itself should fix,
   but a hard blocker for the flow actually working beyond the one
   service tested.
6. **No TypeScript/build/lint/frontend test output** — none of these
   apply since no frontend work was done this pass.
7. **Booking list pagination not exercised beyond a single page** of 2
   real bookings — page/page_size params exist but weren't tested against
   >20 bookings.

## What is solid and fixed this pass
- 6 real, confirmed, flow-blocking backend bugs found and fixed (see
  `HS7_CUSTOMER_BOOKING_FLOW_REPORT.md`), the most severe being that
  **the customer booking flow's very first step could never succeed**
  (empty `MasterOffering` table) and **the confirmation step could never
  succeed** (dead `mark_ready_for_confirmation` code + 4 missing DB
  columns) — i.e., this flow was completely non-functional before this
  pass, despite Sprint 16/HS6/HS6B having built and "certified" pieces of
  it individually.
- Full 8-step flow live-verified end-to-end via real HTTP `curl` against
  the real database, including 2 independent real bookings created.
- Both hard gates (no booking without a still-bookable provider, no
  customer-editable price) live-verified in both the pass and reject
  direction.
- Internal provider-scoring leak to the customer found and fixed on 2
  endpoints.
- Zero regressions in the targeted 415-test sweep after fixing 2
  test-fixture breaks caused by the `MasterOffering`→`MasterService`
  rename (documented, not silently patched over).
