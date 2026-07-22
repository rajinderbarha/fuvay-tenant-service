# Privacy/PII Review — Slice 2F-11 (Workstream 12)

## Fields present
`RealEstateLead.customer_snapshot`/`requirement_snapshot`/
`lead_score_snapshot`/`provider_snapshot` (JSONB blobs — likely
containing customer name/phone/budget/requirement details, though the
exact shape is opaque JSONB, not individually normalized columns);
`RealEstateLeadNote.note_text`/`is_customer_visible`.

## Verified this slice
- **Tenant staff access follows proven delegation**: `require_owner_or_office_staff_mutation`
  (fixed this slice) + `_assert_agent_owns_lead` (existing) together mean
  only the tenant's own assigned agent (or tenant_owner/staff of that
  same tenant reaching the read routes) ever sees a given lead's PII —
  re-verified via `TestAgentMutationRoleGate`/`TestReadRouteRoleGate`.
- **Technicians do not see lead context at all for mutations**: excluded
  entirely from the mutation guard. For the 3 read routes
  (`agent_timeline`/`provider_timeline`/`provider_notes`), technician IS
  currently admitted by `require_staff_or_above` (broader read guard) —
  this is a deliberate choice (reads are lower-risk, and no evidence
  proves technician must be excluded from real-estate lead reads
  specifically, unlike the mutation case where evidence pointed the
  other way). Flagged as a minor, evidence-neutral judgment call, not a
  proven leak — see `product-decisions-required.md`.
- **Internal lead notes are not exposed to customers**: `get_notes(...,
  customer_only=True)` filters to `is_customer_visible == True` only —
  confirmed via direct source read, unmodified, re-verified by the
  existing service-layer test suite.
- **Cross-tenant lead IDs do not leak existence or PII**: the tenant
  filter in `_get_lead` means a foreign-tenant ID simply doesn't match
  any row — `ERR_RECORD_NOT_FOUND`, not a distinguishable "exists but
  denied."
- **Customer sees only their own lead**: `customer_tracking`'s inline
  query filters on both `id` AND `customer_id` together — a foreign
  customer's lead ID returns not-found, no partial data exposure.
- **Audit logs do not contain unnecessary sensitive payloads**:
  `RealEstateLeadExecutionEvent` stores `old_status`/`new_status`/
  `notes`/`event_metadata` — `notes` may contain free-text staff input
  (e.g., a rejection reason), which is expected, proportionate audit
  content, not raw customer PII duplication.

## No proven PII leak found
This slice found no confirmed PII leak in this module — the one
judgment-call item (technician read access) is documented as a product
question, not a security defect, since no proof exists either way and no
evidence suggests it is currently exploited or exploitable beyond
ordinary, tenant-scoped, role-appropriate visibility.
