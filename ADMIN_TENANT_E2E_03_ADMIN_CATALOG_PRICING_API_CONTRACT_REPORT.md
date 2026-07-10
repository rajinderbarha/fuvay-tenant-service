# API Contract Verification (Part 10)

The spec's illustrative `src/lib/api/admin-home-services.ts` does NOT exist — confirmed real module names, all inside the single central `frontend/super-admin/lib/api.ts`:

- `homeServicesCatalogConsoleApi` (listServices, getServiceDetail, getAudit) — used by service-catalog and pricing-rules pages.
- `catalogApi` (listPricingRules, createPricingRule, updatePricingRule, listServiceTypeMappings, listBrandMappings, listTiers) — used by pricing-rules and service-areas pages.
- `masterDataApi` (listIssueTypes, listServiceOptions) — used by service-catalog page (Issues/Options tabs).
- `autoPriceOptionsApi` (getConfig, previewPriceExperience) — used by price-experience page.

All four route to the shared `apiFetch<T>()` wrapper (lib/api.ts line 58) which:
- Attaches `Authorization: Bearer <token>` from `localStorage.serviceos_admin_token` when present (confirmed at line 69).
- Handles 401 with a real refresh-token retry flow before clearing session (lines 73-98).
- On non-OK response, parses the real backend error envelope (`error_code`, `detail`, `resolution`, `context`, `request_id`) into `ServiceOSError` (lines 101-112) — this is what feeds `SectionError`'s "Request ID: ..." display on all 4 pages.

Direct-`fetch()` scan of the 4 target pages: zero direct `fetch()` calls found (grep confirmed only unrelated matches like `refetch()` function names). All API access goes through the central client.

Result: PASS — real central API client confirmed, auth + request_id + refresh handling all real, no direct fetch bypass in the 4 in-scope pages, no fake runtime data substituting for a real API.
