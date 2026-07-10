# Direct Fetch / Mock Data Scan Report (Part 12)

## Direct `fetch()` calls bypassing `lib/api.ts`
Grep for real (word-boundary) `fetch(` calls, excluding `lib/api.ts` itself:

```
app/admin/audit-logs/page.tsx:129       fetch(`${API}${TAB_CONFIG[tab].endpoint}?${qs}`, ...)
app/admin/bookings/page.tsx:364         fetch(`${API_BASE}${path}`, ...)
app/admin/commission-records/page.tsx:62 fetch(`${API}/v1/admin/commission-records?${qs}`, ...)
app/admin/customers/page.tsx:304        fetch(`${API_BASE}${path}`, ...)
app/admin/home-services/service-jobs/page.tsx:50 fetch(`${API}/v1/admin/final-records/jobs?${qs}`, ...)
app/admin/payments/page.tsx:71          fetch(`${API}/v1/admin/payments?${qs}`, ...)
app/admin/refund-requests/page.tsx:70   fetch(`${API}/v1/admin/refund-requests?${qs}`, ...)
```
Classification: **runtime-safe but architecturally inconsistent** — all 7 build the base URL from
an `API`/`API_BASE` constant (not hardcoded `localhost`) and attach a real bearer token from
`localStorage`, so they hit the real backend correctly (confirmed working via the route smoke
tests — all 7 pages' routes returned 200 with real data length in Part 6/1). They just don't go
through the shared `lib/api.ts` client (so they miss any centralized error/retry/request_id
handling `lib/api.ts` might add later). Classified as **needs migration later** — not a runtime
blocker, out of scope to touch 7 page-level data-fetching implementations in a shell/nav sprint.

No hardcoded `http://localhost` URLs found in any of the 7 — all use an env-derived `API`/`API_BASE`
constant, consistent with the rest of the codebase.

## Mock data patterns
Grep for `mockTenants|mockServices|mockPricingRules|mockLedger|mockNotifications|fakeAudit|dummyStats|sampleJobs`
across all `.ts`/`.tsx`: **zero matches**.

## `lib/mock.ts`
File still exists (103 lines) but `grep -rln "lib/mock"` across `app/`, `lib/`, `components/`,
`hooks/` returns **zero references** — confirmed still dead/unreferenced, consistent with the
prior sprint's finding. Not deleted (leaving dead, unreferenced files alone is safer than deleting
in a shell-scoped sprint; flagged for cleanup).

## Conclusion
No runtime-blocking mock data found. The only real finding is the 7 pages using direct `fetch()`
instead of the shared API client — a consistency/architecture item, not a bug (all verified
working against the real backend), filed as "needs migration later."
