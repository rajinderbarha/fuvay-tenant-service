"""
Read-only route-registration inspector for the Phase 1A workflow-rearchitecture
decision closure.

Imports the FastAPI app (app.main:app) and recursively walks its route tree.
Routes mounted via app.include_router() in this codebase are wrapped by
FastAPI's `_IncludedRouter` (a dataclass exposing `.original_router`), so a
plain `app.routes` walk only sees ~5 top-level routes (docs/openapi/static
mount). This script recurses through `.original_router` to reach the real
~2300+ registered endpoint routes.

Does NOT touch the database, does NOT mutate any state, does NOT bind a
network port, does NOT run business logic. Safe to run repeatedly.

Usage:
    PYTHONPATH=. python scripts/workflow_rearchitecture/list_routes.py [prefix ...]

If prefixes are given, only matching routes are printed (path + methods).
Otherwise prints a summary count only.
"""
import sys
import json


def walk(router):
    out = []
    for r in getattr(router, "routes", []):
        if type(r).__name__ == "_IncludedRouter":
            out.extend(walk(r.original_router))
        else:
            path = getattr(r, "path", None)
            methods = sorted(getattr(r, "methods", None) or [])
            if path:
                out.append({"path": path, "methods": methods})
    return out


def main():
    try:
        from app.main import app
    except Exception as e:
        print(json.dumps({"error": f"import failed: {e!r}"}))
        sys.exit(1)

    routes = walk(app.router if hasattr(app, "router") else app)
    routes.sort(key=lambda r: r["path"])

    prefixes = [("/" + p.lstrip("/")) for p in sys.argv[1:]]
    if not prefixes:
        print(json.dumps({"total_routes": len(routes)}))
        return

    result = {"total_routes": len(routes), "matches": {}}
    for prefix in prefixes:
        result["matches"][prefix] = [r for r in routes if r["path"].startswith(prefix)]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
