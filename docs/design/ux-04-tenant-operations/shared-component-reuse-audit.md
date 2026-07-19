# Shared Component Reuse Audit

| UX-04 need | Decision |
|---|---|
| Pipeline identity badge | Reused `components/ux03/widgets/PipelineBadge.tsx` unmodified — no duplicate built. |
| Readiness metadata | Reused `components/ux03/widgets/ReadinessTag.tsx` where needed; not yet threaded through every new route (gap, see `known-limitations.md`). |
| Status badge (generic) | Reused `@serviceos/design-system` `StatusBadge` — accepts arbitrary literal strings, so both `Booking` and `ServiceJob` status vocabularies render through it without a merged enum. |
| Page layout (shell/header) | Reused `PageShell`/`PageHeader` from `@serviceos/design-system` — no new page-chrome component built. |
| List/detail pattern | UX-03's `TenantListPage`/`TenantDetailPage` patterns were evaluated but **not** reused for Job Detail Workspace — the required sticky-header + many model-aware sections (16 required sections per spec) didn't fit `TenantDetailPage`'s simpler section-tab shape without forcing a redesign of that shared pattern, which is out of scope to modify mid-phase. Job Detail Workspace uses a bespoke layout instead. Flagged as `REFACTOR_CANDIDATE` in the audit CSV — a future pass should decide whether to generalize `TenantDetailPage` or keep them separate. |
| Everything else (SLA, timelines, assignment/quote/checklist/parts/credit/comms/risk) | New — no UX-03 equivalent existed; built as new `components/ux04/*` files, none duplicating a UX-03 concept. |
