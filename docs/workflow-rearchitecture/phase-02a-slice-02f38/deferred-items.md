# Deferred Items

- Completing the mounted-route census for the remaining ~1,873
  non-canonical mutation routes (261 fully unclassified, 77 more
  spot-check-only) — deferred to a future slice; comparable in scope to
  the entire 2F-35/36/37 program.
- Migration 144 execution — deferred until a real PostgreSQL environment
  is available.
- Demo-account remediation — deferred until a human decision is recorded
  per `manual-role-confirmation-request.md`.
- Tracing `workflow_service.py`'s `tenant_manager` metadata fields through
  the workflow engine's own enforcement code, if any.
- A dedicated `verify_2f38.py` with all ~25 mission-specified failure
  conditions and negative fixtures.
- A second full-backend-regression run for determinism.
- N01 domain-integrity remediation, payments financial-ledger design,
  read-path privacy fixes, Booking Exception Resolution, cancellation/
  rescheduling — all explicitly out of this slice's scope, unchanged.
