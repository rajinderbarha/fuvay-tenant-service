# Service-Layer Bypass Report

## Scope, honestly stated
Per the brief's own acknowledgment ("a full audit of all ~140 engine service classes may be too broad for one slice"), this slice reviewed the service methods directly touched by this slice's one real code change (`AuthService.update_permissions`) plus re-confirmed the 3 methods spot-checked in Slice 2E. A full caller-graph audit of the ~24 router modules' underlying service methods (the scale Workstream 8 technically asks for) was not completed — see `known-limitations.md`.

## Confirmed safe (re-verified/extended this slice)
- **`AuthService.update_permissions`**: tenant-ownership check (`user.tenant_id != tenant_id`) confirmed intact after this slice's edit — proven by `tests/test_phase2f_mutation_enforcement.py::test_cross_tenant_target_still_rejected`. The new session-revocation logic reads `target_user_id`/`tenant_id` from the same already-validated variables, introducing no new trust boundary.
- **`AuthService.deactivate_staff`** (read, not modified): confirmed it already has its own session-revocation call (`UserSession.revoked_at`), but — newly discovered this slice — **it has the same Redis-flag gap** `update_permissions` had before this slice's fix: it revokes the DB row but never writes `serviceos:session:revoked:{session_id}`, meaning a staff deactivation today does not immediately stop an already-issued JWT from authenticating, contrary to what its own success message might imply ("all sessions revoked"). **Not fixed this slice** (out of the bounded scope — this slice's fix targeted `update_permissions` specifically per Workstream 9's explicit list) — flagged in `known-limitations.md` and `deferred-items.md`.

## Not audited this slice
The service methods underlying the 175 not-fully-protected mutation endpoints across the 24 router modules found in `mutation-enforcement-matrix.csv` — whether each correctly derives `tenant_id` from the authenticated principal (not a request body field) and checks object ownership, was not traced per-endpoint. This is the same class of work `tenant-mutation-endpoint-inventory.csv` documents as needed, not newly discovered as absent.

## Recommendation
A future slice should pick one domain at a time (e.g., starting with the highest-endpoint-count module, `tenant_engine.router` at 27 endpoints, or the `execution.home_service_router`/`home_service_assignment` overlap flagged in `alternate-route-bypass-report.md`) and trace its service methods' callers exhaustively before applying a guard — this keeps each increment reviewable and safe, rather than attempting all 24 modules simultaneously.
