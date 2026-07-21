# Visual Runtime Evidence — UX-06 Round 5

## Reused from Round 4 (still valid, `round3-runtime-evidence/r4-*.png`)

Login, Home, Bookings tab, Profile tab, Chat entry, chat session start,
language selector, categories, offerings, issue/address form, serviceability
+ price (real ₹82) — all captured live in Round 4, light theme, 390px
viewport, real production navigation (not dev showcases).

## Not captured this round

A fresh Round 5 sweep covering the corrected confirm-endpoint flow, the new
tier-selection UI, the new Service Detail screen, Notifications with real
data, Booking Detail's rewritten design, and any dark-theme evidence was
planned but **blocked by a genuine backend outage** partway through this
round (`http://localhost:8000` unreachable, confirmed via repeated
connectivity checks over an extended window — see
playwright-runtime-report.md / known-limitations.md). This is an
infrastructure interruption, not a decision to skip the work.

Dark theme specifically: not applicable regardless of the outage — this app
has no dark-theme implementation at all (see light-dark-runtime-report.md,
unchanged finding from Round 4).

320px-width and large-text-scaling evidence: not captured in any round to
date — a real, standing gap, not newly introduced this round.
