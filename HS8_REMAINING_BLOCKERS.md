# HS8 — Remaining Blockers

1. **No tenant/provider-facing frontend UI** for the job queue, technician
   assignment modal, or status-update actions — only backend endpoints
   were fixed and verified this pass.
2. **No technician mobile/web app UI** for the job card, status CTAs, or
   completion-proof form.
3. **No admin operations dashboard UI** (`/admin/home-services/operations`
   or equivalent) — only 2 job-scoped backend timeline endpoints verified.
4. **Parts request flow is minimal** — technician can flag "parts
   required" (collapses into the generic `quote_required` status) but
   there is no structured parts-request record, no cost/quantity fields,
   and no tenant-side approve/reject action. See `HS8_PARTS_REQUEST_REPORT.md`.
5. **Completion is not a single validated action** — `/work-done` takes
   no payload; work summary, collected-amount validation, and
   conditional photo requirements from the ticket don't exist as
   enforced rules. See `HS8_COMPLETION_PROOF_REPORT.md`.
6. **Customer tracking timeline under-reports real events** — only shows
   assignment-engine events, not the richer execution-engine event
   stream, even though the top-level `status` field is accurate.
7. **Permission-aware UI/RBAC not investigated** — endpoints gate on
   authentication only in what was exercised this pass; granular
   permission enforcement (`tenant.jobs.assign`, `staff.jobs.complete`,
   etc.) wasn't checked.
8. **No standalone `/admin/home-services/jobs` list endpoint** found —
   only job-scoped timeline endpoints.
9. **Wrong-tenant technician rejection** confirmed only by code
   inspection (`validate_staff_eligibility`'s `wrong_tenant` check), not
   a live negative-path curl call.

## What is solid and fixed this pass
- **3 severe, confirmed, previously-undetected bugs** that made the
  entire provider/technician job workflow non-functional:
  1. Every provider-side job-assignment endpoint (8 handlers) scoped
     queries by the wrong ID (`user.user_id` instead of `user.tenant_id`),
     so a real tenant login could never see or manage any of their own
     jobs.
  2. Every technician-side "my jobs" endpoint (5 handlers) matched
     against the wrong ID (raw auth user ID instead of the real
     `provider_team_members.id`), so a real technician login could never
     see a job assigned to them.
  3. The entire technician execution/status-transition router (13
     handlers covering on-the-way through work-done, notes, media,
     parts/quote flags) referenced a `UserContext.staff_member_id`
     attribute that **does not exist**, crashing every single call with
     a 500.
- 3 more missing-`updated_at`-column tables found and fixed (migrations
  125-127), continuing the pattern discovered in HS7.
- Invalid status transitions now correctly return clean 422s with
  `request_id` instead of raw 500s.
- Full technician lifecycle (accept → on-the-way → reached-site →
  inspection → service → work-done) live-verified end-to-end against a
  real job created by the real HS7 booking flow, including customer
  tracking correctly reflecting the live status and payment mode
  remaining unchanged throughout.
- Zero regressions; 5 pre-existing tests updated to match the corrected
  (ServiceOSException-based) error contract, documented inline; 72/72
  passing in the directly affected test file.
