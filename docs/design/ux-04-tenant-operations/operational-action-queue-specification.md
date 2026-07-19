# Operational Action Queue Specification

Type: `OperationalActionItemView` (`lib/ux04/types.ts`). Component:
`components/ux04/OperationalActionQueue.tsx`.

Fields: `entity` (typed `EntityLinkView`, always links to a real pipeline
item — booking or service job — never a generic untyped id), `summary`,
`sla` (`SLAStateView`), `requiredAction` (human copy of what's blocking),
`actions` (`ActionPermissionView[]`, drives whether a control renders).

Ordering/filtering by SLA severity was not implemented client-side this
pass (the fixture list is small and unsorted) — a real implementation
should sort `breached` > `at_risk` > `approaching_deadline` > others, and
this is noted as a deferred item, not a design decision to leave unsorted.
