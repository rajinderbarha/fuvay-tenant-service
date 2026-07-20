# My Work Architecture

My Work is the primary operational queue for every role — not a notification feed. Each item is actionable and points to a workspace.

## Classification buckets (all roles)
Urgent · Requires my action · Waiting for someone else · Scheduled · Recently completed · Escalated · Failed

## Item schema
title, record_reference, current_status, problem/requirement, responsible_role, time_remaining, sla_status, recommended_next_action, primary_action, secondary_action, destination_workspace, permission_required

## Role-specific item sources (evidence-backed, from workflow-inventory.csv)

### super_admin
- Business verification pending → Businesses > Approval workspace (`Tenant.status=pending_review`)
- SLA breach/at-risk complaint → Operations > Complaint workspace (driven by `app.jobs.complaint_sla` loop, RUNTIME_VERIFIED as live)
- Low-credit tenant flagged → Finance > Usage Credits (HS9 low-credit policy, RUNTIME_VERIFIED)
- Security incident → Governance > Audit (AuthAuditLog)
- Duplicate/legacy-engine cleanup tasks (internal, from canonical-pipeline-report.md) — NOT customer-facing, tracked separately in workflow-implementation-roadmap.md, not surfaced in My Work

### tenant_owner
- Quote awaiting approval is customer-side only today (no tenant approval step exists) — so tenant_owner's My Work instead surfaces: provider not assigned / no match found; complaint requires response; low credit balance; staff invite pending acceptance; document expiring/rejected.

### staff
- Same as tenant_owner, scoped to items assigned to them if permission-limited.

### technician
- Job assigned, awaiting accept/reject (notification wired L5-25)
- On-the-way not yet started for a scheduled job
- Job flagged quote_required, awaiting customer decision (waiting-for-someone-else bucket)
- Job ready to complete (proof upload pending)

### customer
- Quote awaiting your approval (RUNTIME_VERIFIED, quote_checklist)
- Invoice due (L5-26 notify wired)
- Provider matching in progress / no match found
- Review request after completed job

## Implementation note
No dedicated "My Work" endpoint exists in the backend today. This requires a new aggregation endpoint per role — see `aggregation-endpoint-recommendations.md` for the proposed `/v1/{role}/my-work` read-only BFF pattern, composing existing status fields from Tenant, ServiceJob, Complaint, quote_checklist, and usage_credits records rather than any new business logic.
