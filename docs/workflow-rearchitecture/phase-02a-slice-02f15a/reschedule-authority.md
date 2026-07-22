# Booking Reschedule Authority

Three routes, two distinct personas:

| Route | Persona | Permission | Guard after 2F-15A |
|---|---|---|---|
| `request_reschedule` | DUAL (customer initiates; tenant may also propose) | `BOOKING_RESCHEDULE` (granted to both `customer` and `tenant_owner`) | `require_tenant_mutation_permission(BOOKING_RESCHEDULE)` |
| `accept_reschedule` | TENANT_ONLY (provider approves the proposed new slot) | `TENANT_UPDATE` (tenant_owner-only) | `require_tenant_mutation_permission(TENANT_UPDATE)` |
| `reject_reschedule` | TENANT_ONLY (provider rejects the proposed new slot) | `TENANT_UPDATE` (tenant_owner-only) | `require_tenant_mutation_permission(TENANT_UPDATE)` |

**Rationale for classifying accept/reject as tenant-only:** `TENANT_UPDATE` is not granted to `customer` anywhere in `ROLE_PERMISSIONS` — a customer proposing their own reschedule cannot also be the one who accepts/rejects it (that would be self-approval). This mirrors the general pattern across the codebase where a proposal/response pair is split across two different personas (e.g. quote send/approve).

**Fix applied:** all three previously used `require_permission(...)` (permission-only, no access-scope awareness); all three now use `require_tenant_mutation_permission(...)`, closing the same access-scope gap already fixed for the create/confirm/convert chain in Slice 2F-15.

No new permission, role, or scope was introduced.
