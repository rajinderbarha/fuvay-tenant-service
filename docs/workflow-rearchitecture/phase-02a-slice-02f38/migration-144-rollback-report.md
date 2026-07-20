# Migration 144 Rollback Report

**Not executed** — no apply occurred (see `migration-144-apply-report.md`),
so no rollback was attempted. Static review of `downgrade()` (see
`migration-144-static-audit.md`) shows a trivial constraint-drop with no
data-loss risk, but this has not been runtime-verified.
