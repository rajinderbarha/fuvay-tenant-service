# Customer Booking Verification (Workstream 5 re-verify)

Re-verified live this round as part of the Workstream 19 E2E proof, not
independently re-run beyond that. The full UX-06 canonical 11-step booking
sequence was replayed via direct curl calls against the real backend and
produced a genuinely new real booking (`BK-20260721-000008`). See
`live-e2e-evidence.md` steps 1-9 for the complete sequence and
`real-record-evidence.csv` for every ID. The UX-06 bargain-optional backend
fix (`bargain_available` flag, standard-price fallback) was confirmed still
live and working exactly as UX-06 documented it.

No separate Playwright/UI-level re-run was performed this round (curl-only,
time-budget decision) — see `live-e2e-evidence.md`'s "Not attempted this
round" section.
