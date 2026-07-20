# Technician Read Policy — Slice 2F-11A (Workstream 3)

For the 3 provider/agent read routes, answering the mission's 10 questions:

1. **Is there a technician/mobile caller?** No — confirmed by
   repository-wide grep (`frontend-mobile-caller-audit.md`); no mobile
   app or staff-app references any `real-estate-leads` path.
2. **Is the technician assigned to the lead?** N/A — no technician-lead
   assignment concept for reads was ever established; `agent_id` is the
   assigned staff/agent, and there is no separate technician-assignment
   field on `RealEstateLead`.
3. **Is assignment checked by the query or service?** No — `get_timeline`/
   `get_notes` filter only by `tenant_id`, not by `agent_id`/assignment,
   for any caller (owner, staff, or, previously, technician).
4. **Does the response contain customer PII?** No — `RealEstateLeadExecutionEvent.to_dict()`
   and `RealEstateLeadNote.to_dict()` contain no customer name/phone/
   email/budget fields (see `pii-field-visibility-matrix.csv`).
5. **Does the response contain provider-internal notes?** Yes, for
   `provider_notes` — it returns ALL notes for the tenant's lead
   (internal and customer-visible alike), which is correct for a
   business-side read (the provider's own internal notes about their own
   lead).
6. **Is business-wide technician access explicitly supported by a
   permission or workflow?** No — no `REAL_ESTATE_*` permission exists at
   all (confirmed, unchanged from Slice 2F-11), and no workflow evidence
   (frontend, mobile, tests) supports technician involvement.
7. **Can an unassigned technician enumerate or read leads?** Previously,
   yes (any technician in the tenant, since the query had no assignment
   filter and technician was admitted by `require_staff_or_above`). Fixed
   this slice — technician is now denied entirely at the persona layer.
8. **Can a technician change the lead ID in the URL to read another
   record?** Moot now (technician denied outright); before the fix, yes
   — any lead ID within the technician's own tenant would have returned
   data, since no assignment filter existed on the read query.
9. **Does tenant filtering alone prevent inappropriate same-tenant
   access?** No — tenant filtering only prevents cross-tenant access; it
   does nothing to limit *which* leads within the tenant a given
   individual may read. This is exactly why the persona-layer fix
   (excluding technician entirely, since no evidence supports even
   business-wide technician visibility) was the correct minimal
   correction, rather than attempting to bolt on an assignment filter
   that would contradict the owner/staff business-wide read pattern.
10. **Is customer data minimized for technician responses?** Moot —
    technician cannot reach these routes at all now.

## Final disposition per route
`agent_timeline`, `provider_timeline`, `provider_notes`: **TECHNICIAN_DENIED_NO_EVIDENCE**
— fixed via `require_owner_or_office_staff_read`.

## Why not ASSIGNED_TECHNICIAN_ALLOWED
Building an assignment-filtered technician read path would require (a)
inventing an assignment concept for reads that doesn't currently exist
for this domain, and (b) product evidence that technician involvement in
real-estate leads is intended at all — neither exists. Per the mission's
explicit constraint ("do not invent a new technician UI or serializer
without evidence"), the correct minimal fix is exclusion, matching the
identical, already-approved standard used for all 11 mutations.
