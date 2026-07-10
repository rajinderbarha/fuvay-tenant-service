# ADMIN-TENANT-E2E-09B — API Contract Report

- All tenant service-setup calls go through the central `lib/api.ts` client
  (`homeServicesSetupApi`, `providerServiceAreasApi`, etc.) — confirmed via grep, no direct
  `fetch()`/`axios`/`XMLHttpRequest` calls in `app/(tenant)/tenant/setup/services/page.tsx` or
  `app/(tenant)/provider/service-coverage/page.tsx` (only `.refetch()` calls through
  `useApi`/`useAction` hooks, which route through the client).
- Auth token and tenant context are injected centrally in `apiFetch` (`lib/api.ts`), unchanged
  by this sprint.
- `request_id` is present on every real error response observed in this sprint's live curl
  testing (e.g. `"request_id":"req_ba32111b922b"` on the 403 responses) — the shared
  `ServiceOSException` error shape always includes it.
- 403 surfacing in the UI: the wizard's existing `ErrBanner` component (already used for
  save/publish errors) displays `saveError` + `saveRequestId` from a caught
  `ServiceOSError` — a read-only user who somehow reaches a disabled button's underlying
  action (e.g. programmatically) would see this same friendly banner with the real backend
  detail message ("Your account has read-only access...") and request_id, not a raw/broken
  error. Not independently re-screenshotted triggering this exact path in this sprint (the
  button is disabled so a normal user cannot trigger it) — verified via code read of
  `ErrBanner` + `handleSaveDraft`'s catch block instead.
- Mutations refetch readiness/coverage/pricing after a successful save: `onSaved` callback in
  the setup page calls `refetchAll()`/`notify(...)` (pre-existing, unchanged, verified present).
- No fake data anywhere in the touched code paths (see Mock Data Rescan).
