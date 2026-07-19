# Compliance & Audit Pattern

## Compliance
List: `/dev/ux-02/compliance` (`EnterpriseListPage<ComplianceCaseFixture>`) — columns Case
(links to detail), Severity, Status, Assigned To, Opened.
Detail: `/dev/ux-02/compliance/[id]` (`EnterpriseDetailPage` + `ReviewApprovalWorkspace` for
resolution) — second real usage of both reusable patterns.

## Audit Explorer
`/dev/ux-02/audit`. Fields per entry: timestamp, actor, role (canonical role), tenantId,
action, resource, result (success/failure/denied via StatusBadge), IP/device, correlation ID,
risk, and a redacted JSON details viewer (`detailsRedacted`, expand/collapse per row).

## Fixture safety
`FIXTURE_AUDIT_ENTRIES.detailsRedacted` contains only synthetic key/value pairs — no real secrets,
tokens, or production identifiers, consistent with the redaction requirement.

## Readiness
Both `MOCK_DESIGN_ONLY` — audit coverage across engines is confirmed partial (not every engine
emits structured audit records today); see `backend-contract-dependencies.md`.
