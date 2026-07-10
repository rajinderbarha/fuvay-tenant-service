# ADMIN-TENANT-E2E-11 — Tenant Settings Report

Route: `/settings` (5 tabs: General Settings, Webhooks, Delivery Log,
Privacy & Data, Security — a larger, real surface than the ticket's
assumed 3 sub-routes).

## Checks
1. Route opens — 200, browser-verified.
2. Real tenant profile/settings data — General Settings tab shows real
   `settingsApi.get()`-backed key/value/source rows with badges
   (Your Override / Plan Default / Platform Default / System Default).
3. Editable fields save — Edit modal wired to `settingsApi.update()`,
   real mutation + refetch (not exercised live this pass to avoid
   mutating shared seed state beyond the scoped RBAC test).
4. Read-only role cannot mutate — **fails**, see the dedicated RBAC
   report — this is the sprint's one real blocker.
5. Notification preferences save — live at `/notifications` → Channels
   tab (`notificationsApi.setChannel()`), not under `/settings` itself;
   functionally present, just organized differently than the ticket
   assumed.
6. Theme/language preferences — theme toggle exists in the topbar
   (dark/light), persists via `useTheme()`; no language preference
   feature exists (not found anywhere in the app) — documented gap, not
   a defect (never claimed to exist).
7. Security settings don't expose secrets — confirmed: API key creation
   shows the raw key exactly once in a "Key Created" modal with an
   explicit one-time warning (`secKeyResult.warning`), matching standard
   secret-handling practice; subsequent views only show `key_prefix`.
8. No fake settings data — confirmed, real API-backed throughout all 5
   tabs (webhooks, delivery log, consent/export/deletion requests under
   DPDP Act 2023, API keys, IP blocklist check, activity reporting — all
   real, working, previously-built functionality, not stubs).

## Verdict
The page itself is a genuinely substantial, real, working settings
surface. The one failure (#4, read-only mutation) is the sprint's
central RBAC finding, documented separately and driving the final
verdict.
