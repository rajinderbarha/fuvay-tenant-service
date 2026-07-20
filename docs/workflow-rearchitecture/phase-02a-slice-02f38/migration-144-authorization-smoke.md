# Migration 144 Authorization Smoke Test

**Not executed** — same blocker as `migration-144-authentication-smoke.md`.
Static and mocked-session test evidence for authorization behavior exists
in `tests/test_phase2f*.py` (2445/2445 passing, see
`phase2f-regression-report.md`) but that suite mocks the database session
and does not exercise this migration's actual PostgreSQL runtime behavior.
