# Product Decisions Required

1. **Route consolidation** — which of each duplicate-route cluster in
   tenant-route-duplication-map.csv becomes canonical (e.g. `/jobs` vs
   `/service-jobs`, four service-area routes, three catalog routes).
2. **"Wallet" naming** (`/wallet`, `/provider/wallet`) — needs explicit
   product review given the platform does not process on-site job payments;
   renaming alone isn't sufficient without confirming what capability the
   page is meant to expose.
3. **Whether/when to wire `UX03_NAV_GROUPS` into production** `layout.tsx`
   and `lib/nav-config.ts`.
4. **Booking/Job pipeline cancellation** — which pipeline (or neither) gets
   real cancel/reschedule support, and whether the two pipelines are ever
   meant to converge product-side.
5. **Geo/service-area mutation scope** — which specific zone-mutation
   actions fall inside the "frozen slice" of closed authorization vs. which
   remain read-only-by-default.
6. **`/ai-chat`, `/settings/engines`, `/marketing/campaign-impact`,
   `/marketing/visibility`** — confirm whether these are real shipped
   tenant-facing features or internal/dev tooling before including them in
   any redesigned nav.
