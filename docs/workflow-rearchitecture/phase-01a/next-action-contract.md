# Decision 9 — Next-Action Contract

Canonical response shape for all 10 domains. Every field marked Stored / Derived / Aggregated / Permission-filtered.

## Universal response shape

```
{
  "current_status": "stored",
  "user_facing_status": "derived",
  "progress": "derived (e.g. 6/12 setup steps complete)",
  "blocking_issue": "derived",
  "blocking_description": "derived",
  "responsible_role": "derived",
  "assigned_user": "stored (if present on record)",
  "recommended_action": "derived",
  "available_actions": "permission-filtered",
  "required_permissions": "stored (P.* constants)",
  "due_at": "stored (where SLA exists) | null",
  "sla_state": "derived",
  "next_destination": "derived (maps to nav workspace)",
  "confirmation_required": "derived (per action, static rule table)",
  "expected_result": "derived (template text per action)",
  "unsupported_reason": "derived — populated ONLY when a spec-requested capability has no backend support (e.g. Parts Approval), explaining why the action is absent rather than silently omitting it"
}
```

## Per-domain specifics

### Business onboarding
- current_status: stored (`Tenant.status`)
- progress: aggregated (profile/docs/services/pricing/coverage/team/package completeness flags)
- blocking_issue: derived (first incomplete required step)
- available_actions: submit, resubmit, view feedback
- next_destination: Business Onboarding wizard

### Business approval
- current_status: stored (`Tenant.status`)
- available_actions: approve, request_changes, reject (permission-filtered to super_admin/admin_operations with tenant-approve permission)
- expected_result: "Tenant will be activated and notified" / "Tenant will be notified of required changes" / "Tenant application will be rejected and notified"
- next_destination: Business Approval workspace

### Provider setup
- progress: aggregated (12-step completeness, see provider-setup-final-contract.md)
- blocking_issue: derived (first incomplete step; publish-readiness gate is the authoritative final check, RUNTIME_VERIFIED existing)
- next_destination: Provider Setup wizard

### Booking
- current_status: stored, from whichever record is designated CANONICAL (see booking-job-canonical-decision.md) — **BLOCKED for full implementation until that decision closes**
- available_actions: cancel, reschedule (both RUNTIME_VERIFIED delivered), track
- unsupported_reason: populated for any exception action not yet backed (e.g. "Retry matching" if no explicit retry endpoint is confirmed)

### Job
- current_status: stored (`ServiceJob.status`)
- available_actions: permission-filtered by role (technician: advance status; tenant_owner/staff: reassign; customer: cancel/reschedule/confirm)
- sla_state: derived — none confirmed at job level today (only complaint-level SLA loop exists), so this returns "none" honestly rather than fabricating a value

### Quote
- current_status: stored (`quote_checklist` item status)
- available_actions: approve, reject, request_revision (customer); create, revise (tenant/staff)
- expected_result: "Job will proceed to work" / "Technician will be asked to revise the quote"
- **Parts Request (sibling capability, corrected from Phase 1's finding of no such entity):** real `PartsRequest` records (status: requested/approved/rejected/installed) exist per job, separate from the quote. available_actions for a parts request: request (technician), approve/reject (tenant/staff), install (TBD by permission). See `quote-parts-scope-decision.md`.

### Complaint
- current_status: stored (`Complaint.status`)
- due_at / sla_state: stored/derived — this is the one domain with a confirmed live SLA engine (`app.jobs.complaint_sla`)
- available_actions: propose, accept, reject, escalate, close (permission- and role-filtered)

### Finance risk
- current_status: derived (e.g. "low_credit" flag) rather than a single stored enum
- available_actions: top_up, adjust (permission-filtered)
- next_destination: Finance > Usage Credits

### Compliance request
- current_status: stored (`ComplianceRequest.status`)
- due_at: stored (DPDP statutory deadline)
- available_actions: fulfill, extend, reject (permission-filtered)

### Security incident
- current_status: stored (`AuthAuditLog` flagged entry)
- available_actions: review, escalate, dismiss (admin_security only)
- unsupported_reason: populated if no formal "incident" status field exists yet on the audit log (SOURCE_INFERRED — audit log stores events, not incident lifecycle; confirm before implementation)

## Implementation rule
`unsupported_reason` must be populated (not the field simply omitted) whenever the spec requests a capability that has no real backend support — this is how Decision 5 (Parts) and any other confirmed gap surface honestly in the UI instead of via a silently-missing button.
