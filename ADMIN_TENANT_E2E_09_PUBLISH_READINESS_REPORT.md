# ADMIN-TENANT-E2E-09 — Publish Readiness Report

Readiness is implemented in two places, both real and backend-driven, not client-only stubs:

1. **Service Setup wizard (`services/page.tsx`) Review step**: publish is gated on `hasActiveArea` (`areasApi.data.areas.some(a => a.is_active)`) — the Publish button is literally `disabled={!hasActiveArea}` and relabels itself "Publish (add area first)" when incomplete. After a real publish call, the UI calls `providerStatusApi.refresh()` (a genuine backend refetch, not a cached/optimistic no-op) and displays `is_bookable`/`bookability_blockers` returned fresh from the server, with an explicit fallback message ("couldn't confirm bookability") if the refresh itself fails — this proves refresh is a real network round-trip, not a local flag flip.

2. **Service Coverage page `ReadinessTab`**: 6 checks (service enabled, type selected if required, brand selected if required, service option active, active area mapped, coverage published) computed from live hook data (`typesApi`, `brandsApi`, `optionsApi`, `areasApi`), each with a "Fix" deep-link to the relevant tab/route when incomplete.

Missing items show a clear reason string (e.g. "At least one type selected", "Active service area mapped") with an `XCircle` icon; completed items show `CheckCircle2`. All-pass state shows a green banner ("All readiness checks passed"); incomplete shows amber ("Complete the missing steps below").

Given the real current DB state (AC Repair already published, 141001 area active, both types/brand pricing configured), most readiness checks would currently read PASS in the live UI — except for the newly-discovered credit-balance-at-0 concern (see Baseline report), which readiness as coded does **not** currently check (no credit-balance readiness item exists in either `ReadinessTab` or the wizard's Review step) — this is a real gap: publish/readiness UI does not surface the wallet-balance risk that the backend's own matching eligibility gate depends on.

## Verdict: PASS for the mechanics tested (real refetch, real gating, real reasons) — ONE GAP NOTED: readiness UI does not include a usage-credit-balance check even though the matching backend treats credits as a gating factor. Not a route-breaking failure, so does not trigger NOT_READY_TENANT_PUBLISH_READINESS_FAILED; carried to Remaining Blockers as a scoped enhancement recommendation.
