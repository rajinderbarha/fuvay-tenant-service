"""Slice 2F-26C — qualified adjudication of the eleven hidden-side-effect routes.

Side effects are proven through the QUALIFIED call path: the service class is
taken from the handler's type annotation (or the module's imports), the bound
method is resolved on that exact class, and its body is inspected for real
writes. An unqualified method-name match is never accepted -- that produced
cross-engine collisions in 2F-26.

Persona comes from the Slice 2F-26B resolver (zero unresolved guards,
principal-vs-target tenant direction).
"""
from __future__ import annotations

import ast
import csv
import importlib.util
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26c")
SRC = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26a",
                   "read-only-nonget-revalidation.csv")
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")

WRITE = re.compile(
    r"\bdb\.(add|delete|flush|commit|add_all|merge)\(|\bself\.db\.(add|delete|flush|commit)\(|"
    r"\bsession\.(add|delete|flush|commit)\(|\bdelete\(\s*\w+\s*\)|"
    r"\.status\s*=|\.deleted_at\s*=|\.archived_at\s*=|\.is_active\s*=", re.I)
AUDIT = re.compile(r"_audit\(|record_platform_audit\(|_log_event\(|_write_history\(")
EXTERNAL = re.compile(r"send_email\(|send_sms\(|send_push\(|enqueue\(|\.delay\(|publish\(")


def resolver():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "resolve_guards_2f26b.py")
    spec = importlib.util.spec_from_file_location("resolve_guards_2f26b", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def strip_prose(fn):
    try:
        src = inspect.getsource(fn)
    except Exception:
        return ""
    try:
        t = ast.parse(inspect.cleandoc(src))
    except Exception:
        return src
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                          ast.Module)) and ast.get_docstring(n):
            n.body = n.body[1:]
    try:
        return ast.unparse(t)
    except Exception:
        return src


def qualified_service_methods(fn):
    """(class, method, source) triples reachable from this handler.

    The class is resolved from the parameter ANNOTATION or from the handler
    module's own imported symbols -- never by bare method name.
    """
    out = []
    mod = sys.modules.get(getattr(fn, "__module__", ""))
    code = strip_prose(fn)
    called = set(re.findall(r"\.(\w+)\(", code))

    candidates = []
    try:
        for _, p in inspect.signature(fn).parameters.items():
            a = p.annotation
            if inspect.isclass(a):
                candidates.append(a)
    except Exception:
        pass
    if mod:
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if inspect.isclass(obj) and name.endswith(("Service", "Manager")):
                candidates.append(obj)

    seen = set()
    for cls in candidates:
        if id(cls) in seen:
            continue
        seen.add(id(cls))
        for mname, meth in inspect.getmembers(cls, inspect.isfunction):
            if mname in called and not mname.startswith("__"):
                out.append((cls.__name__, mname, strip_prose(meth)))
    return out


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    R = resolver()
    idx = R.route_index()
    canon = set()
    for r in csv.reader(open(CANON, encoding="utf-8")):
        if r and r[0] in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            canon.add((r[0], R.norm(r[1])))

    targets = [r for r in csv.DictReader(open(SRC, encoding="utf-8"))
               if r["final_class"] == "HIDDEN_SIDE_EFFECT_FOUND"]
    rows, graph = [], []
    for t in targets:
        key = (t["method"], R.norm(t["path"]))
        rt = idx.get(key)
        if rt is None:
            rows.append({"method": key[0], "path": key[1], "endpoint": t.get("endpoint", ""),
                         "behavior": "DISCONNECTED", "persona": "DISCONNECTED_MUTATION",
                         "evidence": "not mounted", "in_canonical": "no"})
            continue
        cls = R.classify(rt)
        methods = qualified_service_methods(rt.endpoint)
        hcode = strip_prose(rt.endpoint)

        db = bool(WRITE.search(hcode))
        aud = bool(AUDIT.search(hcode))
        ext = bool(EXTERNAL.search(hcode))
        proof = []
        for cname, mname, msrc in methods:
            if WRITE.search(msrc):
                db = True; proof.append(f"{cname}.{mname}:write")
            if AUDIT.search(msrc):
                aud = True; proof.append(f"{cname}.{mname}:audit")
            if EXTERNAL.search(msrc):
                ext = True; proof.append(f"{cname}.{mname}:external")
            graph.append({"method": key[0], "path": key[1],
                          "service_class": cname, "bound_method": mname,
                          "write_expr": bool(WRITE.search(msrc)),
                          "audit_expr": bool(AUDIT.search(msrc)),
                          "external_expr": bool(EXTERNAL.search(msrc)),
                          "resolution": "ANNOTATION_OR_MODULE_IMPORT"})

        if db and ext:
            behavior = "DATABASE_AND_EXTERNAL_MUTATION"
        elif db:
            behavior = "DATABASE_MUTATION"
        elif ext:
            behavior = "EXTERNAL_SIDE_EFFECT"
        elif aud:
            behavior = "AUDIT_ONLY_MUTATION"
        else:
            behavior = "PURE_READ_FALSE_POSITIVE"

        persona = {
            "PLATFORM_ADMIN_MUTATION": "PLATFORM_ADMIN_MUTATION",
            "TENANT_PROVIDER_MUTATION": "TENANT_PROVIDER_MUTATION",
            "CUSTOMER_SELF_SERVICE_MUTATION": "CUSTOMER_SELF_SERVICE_MUTATION",
        }.get(cls["persona"], "PRODUCT_DECISION_REQUIRED")
        if key[1].startswith("/v1/public/"):
            persona = "PUBLIC_OR_UNAUTHENTICATED_MUTATION"

        rows.append({
            "method": key[0], "path": key[1],
            "endpoint": getattr(rt.endpoint, "__name__", ""),
            "module": getattr(rt.endpoint, "__module__", ""),
            "behavior": behavior, "persona": persona,
            "admitted_roles": cls["roles"], "tenant_authority": cls["tenant_authority"],
            "tool_persona": cls["persona"],
            "evidence": "|".join(sorted(set(proof))[:4]) or "handler-level only",
            "in_canonical": "yes" if key in canon else "no",
        })

    with open(os.path.join(OUT, "hidden-side-effect-route-adjudication.csv"),
              "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    if graph:
        with open(os.path.join(OUT, "hidden-side-effect-qualified-call-graph.csv"),
                  "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(graph[0].keys())); w.writeheader(); w.writerows(graph)

    from collections import Counter
    print("behavior:", dict(Counter(r["behavior"] for r in rows)))
    print("persona :", dict(Counter(r["persona"] for r in rows)))
    print()
    for r in rows:
        print(f"  {r['method']:6} {r['path'][:44]:44} {r['behavior'][:26]:26} "
              f"{r['persona'][:28]:28} canon={r['in_canonical']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
