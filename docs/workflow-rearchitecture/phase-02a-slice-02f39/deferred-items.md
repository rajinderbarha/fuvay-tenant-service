# Deferred Items

- Complete mounted-route reclassification (261 remaining) — deferred to a
  dedicated future slice, comparable in scope to 2F-35/36/37.
- `test_sprint27_notifications.py`'s 2 chat-access-scoping failures —
  flagged as possibly authorization-adjacent; needs targeted investigation
  a future slice should prioritize given the security-adjacent naming.
- The ~13 remaining pre-existing domain-logic failures (service catalog,
  checklist, complaint eligibility, quote checklist) — deferred to their
  respective domain owners; each root cause is identified in
  `remaining-failure-disposition.csv` sufficiently to hand off.
- `test_versions.py`'s 2 frontend version-pin failures — deferred to
  whichever UX slice owns the frontend package version decision.
- 2 TypeScript-compile-check failures — deferred to frontend build
  tooling ownership.
- Migration 144 execution — deferred until PostgreSQL is available and a
  human decision is recorded for both demo accounts.
- A dedicated `verify_2f39.py`.
- A second full-backend-regression run for determinism.
