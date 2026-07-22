# Assignment Boundary — Slice 2F-12 (Workstream 6)

## Persona policy per capability

| Capability | Tenant-owner | Canonical staff | Technician | Assigned staff | Platform-admin | Classification |
|---|---|---|---|---|---|---|
| accept/reject/start/complete/no-show/reschedule/notes (7 mutations) | allowed | allowed | **DENIED** | required (assignment-limited) | allowed (via super_admin) | ASSIGNED_CANONICAL_STAFF_ONLY (tenant_owner treated as always-eligible business owner; canonical staff must additionally match assignment) |
| cancel (1 mutation) | allowed | allowed | **DENIED** | not required (business-wide) | allowed | TENANT_OWNER_OR_CANONICAL_STAFF |
| staff_timeline/provider_timeline (2 reads) | allowed | allowed | **DENIED** | not required (tenant-wide read) | allowed | TENANT_OWNER_OR_CANONICAL_STAFF |
| customer_tracking (1 read) | denied | denied | denied | n/a | denied (must use admin_router) | CUSTOMER_SELF_TRACKING_READ |
| admin_timeline (1 read) | denied | denied | denied | n/a | allowed | PLATFORM_ONLY |

## Why technician is denied, not merely unassigned-denied
No mobile/technician caller was found anywhere for this module —
confirmed via repository-wide grep, matching the identical evidence
standard already used for real estate. Technician is excluded entirely
at the persona layer (`require_owner_or_office_staff_mutation`/
`require_owner_or_office_staff_read`), not merely blocked by a missing
assignment — there is no assignment concept for technician in this
domain at all.

## Staff delegation evidence
`tenant_owner`/`staff` are both admitted per
`require_owner_or_office_staff_mutation`'s existing, established
rationale (Slice 2F-6A: back-office capability, no mobile/technician
client evidence) — the same dependency already used for real estate
(Slice 2F-11) and multiple other tenant-facing routers in this codebase.
No new evidence derivation was needed; this is a direct reuse of an
already-proven persona bundle.
