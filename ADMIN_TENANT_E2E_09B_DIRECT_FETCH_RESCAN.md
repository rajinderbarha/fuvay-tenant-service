# ADMIN-TENANT-E2E-09B — Direct Fetch Re-Scan

Grepped touched pages for `fetch(`, `window.fetch`, direct `axios`, `XMLHttpRequest`. Only
matches are `.refetch()` method calls on `useApi`/`useAction` hook results (e.g.
`typePricingApi.refetch()`, `enabledApi.refetch()`) — these route through the central
`lib/api.ts` client, not a bypass. No direct fetch/axios/XHR usage found in
`app/(tenant)/tenant/setup/services/page.tsx` or `app/(tenant)/provider/service-coverage/page.tsx`.
Clean.
