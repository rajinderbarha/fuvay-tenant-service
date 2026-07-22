# Route Enumeration Method

Reused the program's existing, already-validated tooling rather than
building a new enumerator from scratch:

- `scripts/workflow_rearchitecture/list_routes.py` — imports `app.main:app`
  live and recursively walks `_IncludedRouter.original_router` to reach
  every registered endpoint (handles FastAPI's router-wrapping so a
  naive `app.routes` walk, which only sees ~5 top-level routes, is
  avoided). Read-only, no database, no network port.
- `scripts/workflow_rearchitecture/inventory_mutation_routes.py` —
  extends the same live introspection with a dependency-name heuristic
  classifier (identifies HTTP method, auth/permission/scope dependencies,
  and an auto-classification bucket per route).

Both were re-run fresh in this worktree (not reused from a prior slice's
cached output) to confirm the figures are current, not stale.

Manual, evidence-based classification (reading actual router/service
source) was performed for `app/engines/auth/router.py`'s 32
classifier-`UNVERIFIED` routes — see `final-route-classification.csv`.
The remaining 32 modules (229 routes) were not individually
source-inspected this slice; see `known-limitations.md` for the honest
scope statement.
