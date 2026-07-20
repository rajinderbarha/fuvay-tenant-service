# Data-Subject Identity Authority

## Field-by-field classification (Workstream 8)
| Field | Classification | Evidence |
|---|---|---|
| `subject_type` (create_my_request) | `PRINCIPAL_DERIVED` | Router computes it server-side: `"tenant_business" if "business" in request_type else "tenant_owner"` — never read from the request body |
| `subject_id` (create_my_request) | `PRINCIPAL_DERIVED` | `tenant_id_str if subject_type == "tenant_business" else u.user_id` — always the caller's own tenant/user id, never client-suppliable |
| `subject_id` (customer_tenant_response / staff_tenant_response / cancel_my_request / generate_export) | `PARENT_RECORD_DERIVED` | These routes never construct a subject identity — they operate on an EXISTING request row, already tenant/subject-scoped at creation; the route only reads `req.subject_id`, never writes it |
| `subject_id` (withdraw_consent) | `PRINCIPAL_DERIVED` | `actor_id = uuid.UUID(u.user_id)` — the caller's own identity, no request/consent ID path param exists to spoof |
| `email`/`phone` | Not used for identity establishment anywhere in these 6 routes | `subject_email`/`subject_name` are stored for DISPLAY purposes only (`create_my_request` sets them from `u.email`/`u.full_name`) — never used as a lookup/matching key |
| `external_subject_id`/`identity_document` | `UNSUPPORTED` | No such field exists anywhere in this module's schema or routes |

## Requirements checklist
- **Provider cannot select an arbitrary global customer** — TRUE: no
  route in this file accepts a customer/subject identifier as CLIENT
  input at all; `subject_id` is always either the caller's own identity
  or read from an already-tenant-scoped existing row.
- **Provider cannot submit another tenant's customer** — TRUE, same
  reasoning — there is no input vector for this.
- **Data-subject identity tied to an established tenant relationship** —
  TRUE for `create_my_request` (subject IS the tenant/tenant-owner
  itself); for `customer-requests`/`staff-requests` responses, the
  RELATIONSHIP is the pre-existing `metadata_json["related_tenant_id"]`/
  `["tenant_id"]` link established when the underlying request was first
  created (by the customer or by admin), not something these 2 response
  routes establish themselves.
- **Request customer_id cannot override an authoritative parent
  relationship** — N/A structurally: these routes never accept a
  `subject_id`/`customer_id` override field.
- **Email/phone equality alone does not establish account ownership** —
  TRUE, confirmed: `subject_email` is never used as a WHERE-clause
  matching key anywhere in these 6 routes' queries (only `id`,
  `metadata_json["tenant_id"]`, `metadata_json["related_tenant_id"]`, and
  `subject_type` are ever used for scoping).
- **Customer self-service routes derive identity from the authenticated
  principal** — TRUE, confirmed in `customer_router.py` (out of this
  slice's direct scope but re-verified): `user_id = uuid.UUID(u.user_id)`,
  matched against `ComplianceRequest.subject_id` directly (the real
  column, not JSONB).
- **Provider routes cannot impersonate customer self-service decisions** —
  TRUE: `customer_tenant_response` is a DISTINCT capability (tenant
  RESPONDING to a customer's request) from any customer self-service
  action; it never writes to `ComplianceRequest.status` or any field a
  customer's own self-service action would write.
- **Foreign and missing subject records are privacy equivalent** — TRUE,
  see `compliance-read-privacy.md` — the WHERE-clause-based scoping
  produces identical "not found" behavior for both cases across all 6
  routes.

## No tenant-customer directory built
Confirmed: this slice did not add any lookup, search, or listing
capability that lets a tenant browse or select an arbitrary customer —
the only way a tenant reaches a customer's request is via the SAME
pre-established `related_tenant_id` link the customer's OWN request
creation already established (out of this slice's control), consistent
with the OUT OF SCOPE constraint.
