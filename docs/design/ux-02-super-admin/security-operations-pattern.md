# Security Operations Presentation Pattern

Showcase: `/dev/ux-02/security` (`app/dev/ux-02/security/page.tsx`), built on
`EnterpriseListPage<SecurityObservationFixture>`. Readiness: `SECURITY_CONTRACT_PENDING`.

## Status language (never overstated)
`SecurityObservationStatus` in `lib/ux02/types.ts`:
`observation | needs_verification | confirmed_finding | investigating | action_required |
remediated | false_positive | product_policy_blocked`.

A static code/config observation is always presented as `observation` or `needs_verification` —
never rendered as if it were a confirmed live incident. Only `confirmed_finding` /
`action_required` imply a verified problem; `false_positive` and `product_policy_blocked` exist so
the UI can explicitly close out non-issues without deleting the record.

## Columns
Observation title, Status (StatusBadge — falls back to a neutral badge + humanized text for any
status not already in the shared status/color registry, avoiding a second color system), Risk
(dot badge), Detected timestamp, Correlation ID (for cross-referencing Audit Explorer entries).
