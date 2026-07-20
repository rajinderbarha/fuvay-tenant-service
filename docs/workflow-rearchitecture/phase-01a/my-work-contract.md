# Decision 8 — My Work Item Contract (Implementation-Ready)

## Item schema

| Field | Type | Source |
|---|---|---|
| id | string | derived (composite of record_type+record_id+work_type) |
| work_type | enum | derived from record type + status |
| domain | enum (business/service/booking/finance/governance) | derived |
| role | enum (10 canonical roles) | derived from responsible_role at query time |
| priority | enum (urgent/normal/low) | derived from sla_state + age |
| user_facing_title | string | derived (template per work_type, e.g. "Business verification pending") |
| user_facing_description | string | derived (template + record fields) |
| record_type | enum (Tenant/ServiceJob/Complaint/QuoteChecklistItem/UsageCreditLedger/ComplianceRequest) | stored (from source table) |
| record_id | uuid | stored |
| current_status | string | stored (source record's real status field) |
| user_facing_status | string | derived (mapped via status-next-action-registry.csv style lookup) |
| blocking_reason | string\|null | derived |
| responsible_role | enum | derived from record + status |
| assigned_user | uuid\|null | stored (if record has an assignee field, e.g. `assigned_staff_id`) |
| created_at | datetime | stored |
| due_at | datetime\|null | stored where SLA exists (Complaint SLA loop); null otherwise |
| sla_state | enum (on_track/at_risk/breached/none) | derived (Complaint SLA loop is the only confirmed live SLA engine; other domains report `none` until their own SLA fields are confirmed) |
| time_remaining | duration\|null | derived from due_at |
| recommended_action | string | derived (per status-next-action-registry.csv) |
| available_actions | array<string> | permission-filtered at query time |
| primary_action | string | derived (first of available_actions by priority ranking) |
| destination_route | string | derived (maps to final-role-navigation-matrix.csv workspace) |
| required_permission | string | stored (from `P.*` constant backing the action) |
| tenant_id | uuid\|null | stored (null for platform-scoped items) |
| metadata | object | derived (record-type-specific extra fields, e.g. quote amount) |
| completed_at | datetime\|null | stored, null unless in RECENTLY_COMPLETED category |

## Categories

- **URGENT** — sla_state = breached, or priority-flagged by domain rule (e.g. SLA-breached complaint).
- **REQUIRES_MY_ACTION** — current role is `responsible_role` and no blocking_reason.
- **WAITING_FOR_OTHERS** — current role initiated but `responsible_role` is someone else (e.g. tenant waiting on customer quote decision).
- **SCHEDULED** — future due_at, not yet actionable (e.g. scheduled job not yet started).
- **ESCALATED** — complaint/dispute in escalated state (complaints engine has this concept natively).
- **FAILED** — any record with a genuine failure state (e.g. matching found zero providers, deduction failed — none confirmed to have a "failed" status field beyond matching; flag other domains as none until confirmed).
- **RECENTLY_COMPLETED** — completed_at within a rolling window (e.g. 7 days).

## Derivation sources (no new state machine)

My Work does **not** introduce a new workflow-state table. Every item is derived at query time from:
- `Tenant.status` (onboarding/approval domain)
- `ServiceJob.status` + assignment fields (booking/job domain — see booking-job-canonical-decision.md for which record is the source once resolved)
- `Complaint.status` + SLA loop fields (`app.jobs.complaint_sla`)
- `quote_checklist` item status (finance/quote domain)
- `UsageCreditLedger` low-balance flag (finance domain)
- `ComplianceRequest` status + due_at (compliance domain)
- `AuthAuditLog` flagged security events (governance domain)

## Backend requirement
One new read-only aggregation endpoint per role, `GET /v1/{role}/my-work`, composing the above sources through existing scope services (`TenantScopeService`/`StaffScopeService`/`CustomerScopeService`) and existing `require_permission` checks — no new authorization model. See Phase 1 `aggregation-endpoint-recommendations.md` item 1 for the endpoint spec; this document defines the item contract it must return.

## Explicit non-goal
Booking-domain My Work items must reference whichever record is designated CANONICAL in `booking-job-canonical-decision.md` — never Booking (legacy) or field_ops Job.
