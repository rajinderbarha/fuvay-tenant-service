# ADMIN-TENANT-E2E-04B — Legacy Operations Bridge Report

## What changed
`app/admin/operations/page.tsx` — added a persistent banner directly
below the page header:

> "This board shows **Field Ops (legacy)** jobs, a separate lifecycle
> from Home Services bookings. It is empty because no legacy Field Ops
> jobs exist in this environment — this is expected, not broken.
> **View real Home Services Jobs →**"

The banner:
- Always visible (not conditional on empty state alone), so admins
  always understand what this board is and where the real Home Services
  data lives.
- The "It is empty because…" clause only appears when the list is
  genuinely empty and not still loading — avoids a false claim while
  data is in flight.
- The link navigates to `/admin/home-services/service-jobs`.

## Against the ticket's acceptable/not-acceptable outcomes
Acceptable outcome chosen: **#2 + #3** — "Shows clear empty state...
Includes a visible link to Home Services Jobs." (Not #1 redirect, since
Field Ops is a real, separate, intentional module — redirecting away
from it would hide a legitimate admin surface, not just an empty
placeholder.)

Not-acceptable outcomes avoided:
- ~~Empty page that appears broken~~ — now explained.
- ~~Admin cannot discover real Home Services jobs~~ — one click away,
  always visible.
- ~~Fresh completed jobs hidden from operations~~ — the canonical route
  (once its 401 bug was fixed) now shows all 11 real jobs including the
  freshest completion.
- ~~Two job systems with no explanation~~ — banner explains the split.

## Browser-verified
Playwright test: navigated to `/admin/operations`, confirmed the bridge
link is visible, clicked it, confirmed navigation to
`/admin/home-services/service-jobs`. Passing.

## Verdict
Full pass — legacy operations no longer misleads admins.
