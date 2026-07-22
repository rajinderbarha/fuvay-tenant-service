"""Slice 2F-26 — application-wide persona-based mounted mutation sweep.

Route PREFIX is metadata, not persona evidence. This tool classifies every
mounted route by what it actually DOES (AST side-effect analysis of the
handler plus the service methods it calls) and by which principals its
dependency chain actually admits.

Outputs CSVs under docs/workflow-rearchitecture/phase-02a-slice-02f26/.
"""
from __future__ import annotations

import ast
import csv
import inspect
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26")

# ── side-effect markers ─────────────────────────────────────────────────────
DB_WRITE_ATTRS = {"add", "delete", "flush", "commit", "add_all", "merge"}
DB_WRITE_CALLS = {"update", "insert", "delete"}          # sqlalchemy constructs
EXTERNAL_MARKERS = {
    "send_email", "send_sms", "send_push", "notify", "publish", "enqueue",
    "delay", "apply_async", "upload", "delete_file", "put_object",
    "create_order", "capture", "refund", "broadcast", "send_json",
    "credit_wallet", "debit_wallet",
}
AUDIT_MARKERS = {"_audit", "_log_event", "_write_history", "_pkg_audit",
                 "record_platform_audit"}

# Evidence that a handler derives its TENANT from the authenticated principal.
# This -- not the URL prefix -- is what makes a route tenant/provider-facing.
TENANT_DERIVATION_CALLS = {"_tid", "_tenant_id", "_effective_tenant",
                           "_get_review_scoped", "_svc", "_svc_technician"}
TENANT_ATTR_NAMES = {"tenant_id", "actor_tenant_id"}

# Raw SQL that mutates.
RAW_SQL_MUTATIONS = ("insert into", "update ", "delete from", "upsert")


class SideEffectVisitor(ast.NodeVisitor):
    """Collect side-effect evidence from a function body."""

    def __init__(self):
        self.db_writes: set[str] = set()
        self.external: set[str] = set()
        self.audit: set[str] = set()
        self.calls: set[str] = set()
        self.tenant_evidence: set[str] = set()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in TENANT_ATTR_NAMES:
            owner = getattr(node.value, "id", getattr(node.value, "attr", ""))
            if owner in ("u", "user", "actor", "self", "principal"):
                self.tenant_evidence.add(f"{owner}.{node.attr}")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            low = node.value.lower()
            for frag in RAW_SQL_MUTATIONS:
                if frag in low:
                    self.db_writes.add("raw_sql")
                    break
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = None
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
            # db.add / self.db.commit / session.flush
            if name in DB_WRITE_ATTRS:
                owner = node.func.value
                owner_src = getattr(owner, "attr", getattr(owner, "id", ""))
                if "db" in str(owner_src).lower() or "session" in str(owner_src).lower():
                    self.db_writes.add(name)
            if name in EXTERNAL_MARKERS:
                self.external.add(name)
            if name in AUDIT_MARKERS:
                self.audit.add(name)
        elif isinstance(node.func, ast.Name):
            name = node.func.id
            if name in DB_WRITE_CALLS:
                self.db_writes.add(f"sqlalchemy.{name}()")
            if name in EXTERNAL_MARKERS:
                self.external.add(name)
            if name in AUDIT_MARKERS:
                self.audit.add(name)
        if name:
            self.calls.add(name)
            if name in TENANT_DERIVATION_CALLS:
                self.tenant_evidence.add(f"{name}()")
        self.generic_visit(node)


def analyse_fn(fn) -> dict:
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        return {"db": set(), "ext": set(), "audit": set(), "calls": set(),
                "tenant": set(), "src": ""}
    try:
        tree = ast.parse(_dedent(src))
    except SyntaxError:
        return {"db": set(), "ext": set(), "audit": set(), "calls": set(),
                "tenant": set(), "src": src}
    v = SideEffectVisitor()
    v.visit(tree)
    return {"db": v.db_writes, "ext": v.external, "audit": v.audit,
            "calls": v.calls, "tenant": v.tenant_evidence, "src": src}


def _dedent(src: str) -> str:
    lines = src.splitlines()
    if not lines:
        return src
    indent = len(lines[0]) - len(lines[0].lstrip())
    return "\n".join(l[indent:] if len(l) >= indent else l for l in lines)


# ── service-method resolution ───────────────────────────────────────────────
def build_service_index() -> dict[str, list]:
    """Map method name -> [functions] across every engine service module."""
    idx: dict[str, list] = defaultdict(list)
    import importlib
    import pkgutil
    import app.engines as engines_pkg
    for mod in pkgutil.walk_packages(engines_pkg.__path__, "app.engines."):
        if not any(k in mod.name for k in ("service", "_service")):
            continue
        try:
            m = importlib.import_module(mod.name)
        except Exception:
            continue
        for _, obj in inspect.getmembers(m, inspect.isclass):
            if obj.__module__ != mod.name:
                continue
            for mname, meth in inspect.getmembers(obj, inspect.isfunction):
                if mname.startswith("__"):
                    continue
                idx[mname].append((mod.name, meth))
    return idx


SERVICE_INDEX: dict[str, list] = {}


def _engine_of(module: str) -> str:
    """`app.engines.X...` -> `X`; used to prevent cross-engine name collisions."""
    parts = (module or "").split(".")
    return parts[2] if len(parts) > 2 and parts[1] == "engines" else ""


def deep_side_effects(fn, depth: int = 2) -> dict:
    """Handler analysis plus service-method following, SAME ENGINE ONLY.

    Following by bare method name across the whole codebase produced false
    positives: a read handler calling `svc.get_deposit()` picked up writes from
    an unrelated `get_deposit` in a different engine, making pure reads look
    like mutations. Following is now restricted to services in the handler's
    own engine package.
    """
    home = _engine_of(getattr(fn, "__module__", ""))
    agg = {"db": set(), "ext": set(), "audit": set(), "tenant": set()}
    seen: set[str] = set()

    def walk(f, d):
        info = analyse_fn(f)
        agg["db"] |= info["db"]
        agg["ext"] |= info["ext"]
        agg["audit"] |= info["audit"]
        agg["tenant"] |= info["tenant"]
        if d <= 0:
            return
        for call in info["calls"]:
            if call in seen:
                continue
            seen.add(call)
            for mod_name, target in SERVICE_INDEX.get(call, []):
                if home and _engine_of(mod_name) != home:
                    continue          # cross-engine name collision -- skip
                walk(target, d - 1)

    walk(fn, depth)
    return agg


# ── dependency extraction ───────────────────────────────────────────────────
def dep_names(route) -> list[str]:
    names: list[str] = []
    dep = getattr(route, "dependant", None)
    if dep is None:
        return names

    def rec(d):
        c = getattr(d, "call", None)
        if c is not None:
            names.append(getattr(c, "__name__", str(c)))
        for sub in getattr(d, "dependencies", []) or []:
            rec(sub)

    rec(dep)
    return names


AUTH_DEPS = {
    "get_current_user", "require_super_admin", "require_tenant_owner",
    "require_tenant_owner_mutation", "require_customer", "require_technician",
    "require_staff_or_technician_only", "_check", "require_permission",
    "require_tenant_mutation_permission",
}


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    global SERVICE_INDEX
    print("indexing service methods ...")
    SERVICE_INDEX = build_service_index()
    print(f"  {len(SERVICE_INDEX)} distinct service method names")

    from app.main import app
    from fastapi.routing import APIRoute

    def collect(router_or_app, acc):
        """Recurse through _IncludedRouter wrappers via `original_router`.

        FastAPI nests included routers rather than flattening them: a naive
        `for r in app.routes` sees 207 wrapper objects and ZERO APIRoutes,
        which would have produced an empty inventory and a silently wrong
        "no routes found" result. The wrapper exposes the real router as
        `.original_router` (same traversal the pre-existing mutation-inventory
        tool uses).

        Unlike that tool, this collector keeps EVERY method including GET --
        filtering to POST/PUT/PATCH/DELETE up front is precisely the blind
        spot this slice exists to close (a mutating GET would be invisible).
        """
        for r in getattr(router_or_app, "routes", []) or []:
            if type(r).__name__ == "_IncludedRouter":
                collect(r.original_router, acc)
            elif isinstance(r, APIRoute):
                acc.append(r)
        return acc

    all_routes = collect(app, [])
    seen_keys = set()
    rows = []
    print(f"walking mounted routes ... found {len(all_routes)} APIRoute objects")
    for r in all_routes:
        for method in sorted(r.methods or []):
            if method in ("HEAD", "OPTIONS"):
                continue
            if (method, r.path) in seen_keys:
                continue
            seen_keys.add((method, r.path))
            fn = r.endpoint
            eff = deep_side_effects(fn)
            deps = dep_names(r)
            auth = [d for d in deps if d in AUTH_DEPS]
            try:
                src_file = inspect.getsourcefile(fn) or ""
                src_line = inspect.getsourcelines(fn)[1]
            except Exception:
                src_file, src_line = "", 0
            rows.append({
                "method": method,
                "path": r.path,
                "endpoint": getattr(fn, "__name__", "?"),
                "module": getattr(fn, "__module__", "?"),
                "source_file": os.path.relpath(src_file, REPO) if src_file else "",
                "source_line": src_line,
                "tags": "|".join(r.tags or []),
                "deprecated": bool(getattr(r, "deprecated", False)),
                "include_in_schema": bool(getattr(r, "include_in_schema", True)),
                "dependencies": "|".join(deps),
                "auth_dependencies": "|".join(auth) or "NONE",
                "db_writes": "|".join(sorted(eff["db"])) or "",
                "external_effects": "|".join(sorted(eff["ext"])) or "",
                "audit_effects": "|".join(sorted(eff["audit"])) or "",
                "tenant_derivation": "|".join(sorted(eff["tenant"])) or "",
            })

    print(f"  {len(rows)} mounted routes (excl. HEAD/OPTIONS)")
    with open(os.path.join(OUT, "complete-mounted-route-inventory.csv"),
              "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote complete-mounted-route-inventory.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
