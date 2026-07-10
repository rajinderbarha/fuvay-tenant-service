# HS4B — Setup Checklist Status Report

## What was done
`TenantLayout.tsx` (the real, live-rendered setup checklist source —
confirmed in the HS0 sprint) already consumes
`s?.visibility_blockers`/`s?.bookability_blockers` from
`providerStatusApi.get()` in its checklist-progress computation (lines
118, 356 — pre-existing, unchanged this sprint). Because HS4B's fix
makes `GET /v1/provider/status` return real, current data instead of a
frozen empty-array default, **the existing checklist UI now reflects
real bookability status without any checklist-specific code changes** —
it was already wired to read this data, it just never received
anything meaningful before this sprint.

## Live-verified
Confirmed via direct `curl` this sprint: `GET /v1/provider/status`
(the same endpoint `TenantLayout.tsx` calls) now returns real,
current `bookability_blockers` reflecting actual missing setup items
(e.g., `USAGE_CREDITS_INSUFFICIENT`, `SERVICE_AREA_MISSING`) — the
exact shape the checklist component already expects.

## Not independently re-verified this sprint
Did not load `/tenant/setup/checklist` in a browser to visually confirm
the rendered checklist items update after a refresh (no browser session
run this sprint — verification was via direct API calls and source
inspection). The data contract is confirmed correct; the visual
rendering was not screenshotted.

## Verdict
Setup checklist: **now receives real data** (the underlying bug is
fixed), consistent with the ticket's requirement that publish/refresh
should be reflected there. Visual confirmation in a browser: **not
performed**.
