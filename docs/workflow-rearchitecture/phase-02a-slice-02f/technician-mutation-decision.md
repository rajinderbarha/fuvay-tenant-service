# Technician Mutation Decision

## Status: no changes made; findings documented

## Confirmed from the runtime inventory
Technician-facing mutation endpoints (`/v1/staff/*`, `TENANT_TECHNICIAN_MUTATION` classification) total **51** across several router modules (`execution.home_service_router`'s staff-side endpoints, `home_service_assignment.staff_router`, `field_ops.staff_router`, `field_ops.checklist_router`). None of these show the `require_tenant_mutation_permission` guard (expected and correct — that guard is specifically the tenant-owner/staff read-only mechanism, not meant for technician operational actions per se).

## Per the brief's explicit list — status of each, based on prior slices' evidence (not re-verified individually this slice beyond the route inventory)
| Technician action | Confirmed working (prior slices) | This slice's guard-status finding |
|---|---|---|
| Accept/reject assigned work | Yes (Slice 1/2E) | `execution.home_service_router` shows `UNVERIFIED` (no detected route dependency) — same finding as the rest of that module |
| On-the-way / arrival | Yes | Same module, same finding |
| Inspection | Yes | Same |
| Quote submission (`quote-required` flag) | Yes | Same |
| Parts Request creation | Yes (Slice 1, ServiceJob-scoped, tested) | Same |
| Work start/progress/completion | Yes | Same |
| Media/evidence upload | Not independently re-verified this slice | `media.new_router` shows `ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE` (6 endpoints) |

## Why "read-only policy" is correctly NOT applied to technician workflows
Per the brief's own instruction ("do not apply staff read-only policy mechanically to technician workflows") and this slice's own finding that `access_scope`-based read-only enforcement is specifically a tenant-owner/staff-delegation mechanism (not a technician concept) — no technician endpoint was touched or considered for the read-only guard. Technician actions remain governed by `require_technician` (role) plus, per Slice 1's prior verification, ServiceJob-ownership scoping enforced in the service layer (`assigned_staff_id` filtering, confirmed in Phase 2A Slice 1/2B).

## Provider-only Parts installation
Re-confirmed unchanged from Slices 1/2/2B: `POST /v1/provider/service-jobs/{id}/parts-requests/{id}/install` remains the only install endpoint; no technician-facing install action exists anywhere in the inventory (`/v1/staff/*` paths show no `install` endpoint for parts). Consistent with the non-negotiable rule ("Parts installation remains provider-only unless repository evidence changes") — no evidence changed this slice.

## Confirmed, not just inferred: why these show UNVERIFIED and what actually protects them
Checked directly this slice: `app/engines/execution/home_service_router.py`'s `staff_router = APIRouter(...)` has **no router-level `dependencies=[...]`** — so the `UNVERIFIED` classification is accurate at the route-dependency level; there genuinely is no `require_technician`/`require_permission` FastAPI dependency attached to these endpoints. Consistent with Slice 1's original reading of this file: each handler instead resolves `_staff_member_id(user, db)` (mapping the authenticated user to their technician identity) and the **service layer** checks `job.assigned_staff_id` against that resolved id, rejecting the call if they don't match (confirmed present in Slice 1's original investigation of this exact file, re-confirmed by inspection this slice, not re-executed against a live server this slice). This is real ownership enforcement — just implemented as an in-handler/service-layer check rather than a route-level FastAPI dependency, which is why an automated dependency-name scan alone cannot see it. **This is the correct explanation, not speculation** — it also means `service-layer-bypass-report.md`'s broader point stands: guard-status classification from route dependencies alone systematically undercounts real protection for this style of endpoint, and a full per-handler review (not attempted at scale this slice) is needed before treating every `UNVERIFIED` row in `tenant-mutation-endpoint-inventory.csv` as equally risky.
