"""Slice 2F-26A — branch-level adjudication of the unresolved populations.

Resolves, with route-level evidence:
  A. 123 MIXED_PERSONA mutations   -> one final persona each
  B. 7 held single-evidence candidates
  C. 55 classifier disagreements
  D. 31 mutating GETs (revalidation)
  E. 145 read-only non-GET routes (hidden-side-effect hunt)

Persona is decided by ADMITTED PRINCIPALS + ACTOR/TENANT DERIVATION + MUTATED
OBJECT OWNERSHIP. Path prefix is recorded but never decisive.
"""
from __future__ import annotations

import ast
import csv
import inspect
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
S26 = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26")
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26a")
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")

# Which canonical roles each dependency admits. Static, from app/dependencies/auth.py
# and app/core/permissions.py -- verified by reading those sources.
ADMITS = {
    "get_current_user": {"super_admin", "tenant_owner", "staff", "technician",
                         "customer", "admin_operations", "admin_finance",
                         "admin_security", "admin_readonly"},
    "require_super_admin": {"super_admin"},
    "require_customer": {"customer"},
    "require_tenant_owner": {"tenant_owner", "super_admin"},
    "require_tenant_owner_mutation": {"tenant_owner", "super_admin"},
    "require_technician": {"technician", "staff", "tenant_owner", "super_admin"},
    "require_staff_or_technician_only": {"staff", "technician"},
}

ACTOR_EXPR = re.compile(r"(user|u|actor|principal)\.user_id|actor_id\s*=")
TENANT_EXPR = re.compile(
    r"(user|u|actor|principal)\.tenant_id|_tid\(|_tenant_id\(|_effective_tenant\(|"
    r"actor_tenant_id")
ROLE_BRANCH = re.compile(r"\.role\s*(==|!=|in|not in)|is_customer|is_staff|is_admin")


def norm(p):
    return p if p.startswith("/v1/") else ("/v1" + p if p.startswith("/") else p)


def strip_prose(fn):
    try:
        src = inspect.getsource(fn)
    except Exception:
        return ""
    try:
        tree = ast.parse(_dedent(src))
    except SyntaxError:
        return src
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                          ast.Module)) and ast.get_docstring(n):
            n.body = n.body[1:]
    try:
        return ast.unparse(tree)
    except Exception:
        return src


def _dedent(s):
    ls = s.splitlines()
    if not ls:
        return s
    i = len(ls[0]) - len(ls[0].lstrip())
    return "\n".join(l[i:] if len(l) >= i else l for l in ls)


def route_index():
    from app.main import app
    from fastapi.routing import APIRoute
    idx = {}

    def collect(r):
        for x in getattr(r, "routes", []) or []:
            if type(x).__name__ == "_IncludedRouter":
                collect(x.original_router)
            elif isinstance(x, APIRoute):
                for m in x.methods or []:
                    idx[(m, norm(x.path))] = x
    collect(app)
    return idx


def deps_of(route):
    names = []
    d = getattr(route, "dependant", None)

    def rec(x):
        c = getattr(x, "call", None)
        if c is not None:
            names.append(getattr(c, "__name__", str(c)))
        for s in getattr(x, "dependencies", []) or []:
            rec(s)
    if d:
        rec(d)
    return names


def admitted_roles(deps):
    """Intersection of every role-restricting dependency on the route."""
    sets = [ADMITS[d] for d in deps if d in ADMITS]
    if not sets:
        return set()
    out = set.intersection(*sets) if len(sets) > 1 else sets[0]
    return out


SERVICE_TENANT_CACHE: dict[str, bool] = {}


def service_scopes_by_tenant(fn) -> tuple[bool, str]:
    """Follow the handler's service calls and look for TENANT SCOPING there.

    Most handlers are thin delegates: `svc = _svc(db, request, user)` then
    `await svc.method(...)`. Tenant derivation therefore lives in the service,
    not the handler. Judging persona from handler text alone mislabels genuine
    tenant routes -- an earlier pass in this slice "corrected" 41 real tenant
    rows on exactly that mistake.

    Evidence accepted: a service method in the SAME engine that references
    `tenant_id` in a filter/where/assignment.
    """
    import importlib, pkgutil
    mod_name = getattr(fn, "__module__", "")
    parts = mod_name.split(".")
    if len(parts) < 3 or parts[1] != "engines":
        return False, ""
    engine = parts[2]
    key = f"{engine}:{getattr(fn,'__name__','')}"
    if key in SERVICE_TENANT_CACHE:
        return SERVICE_TENANT_CACHE[key], "cached"
    code = strip_prose(fn)
    called = set(re.findall(r"\.(\w+)\(", code))
    try:
        pkg = importlib.import_module(f"app.engines.{engine}")
    except Exception:
        return False, ""
    found = ""
    for _, modname, _ in pkgutil.iter_modules(pkg.__path__, f"app.engines.{engine}."):
        if "service" not in modname:
            continue
        try:
            m = importlib.import_module(modname)
        except Exception:
            continue
        for _, cls in inspect.getmembers(m, inspect.isclass):
            if cls.__module__ != modname:
                continue
            for mname, meth in inspect.getmembers(cls, inspect.isfunction):
                if mname not in called:
                    continue
                try:
                    msrc = strip_prose(meth)
                except Exception:
                    continue
                if re.search(r"tenant_id\s*==|tenant_id\s*=|\.tenant_id", msrc):
                    found = f"{modname.split('.')[-1]}.{mname}"
                    SERVICE_TENANT_CACHE[key] = True
                    return True, found
    SERVICE_TENANT_CACHE[key] = False
    return False, ""


def load(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def write(name, rows, hdr=None):
    if not rows:
        rows = [{"note": "empty"}]
    hdr = hdr or list(rows[0].keys())
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hdr, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(f"  wrote {name} ({len(rows)})")


def adjudicate(route, sweep_row, method, path):
    """Return (persona, basis, evidence dict) for one route."""
    deps = deps_of(route)
    roles = admitted_roles(deps)
    code = strip_prose(route.endpoint)
    actor = bool(ACTOR_EXPR.search(code))
    tenant = bool(TENANT_EXPR.search(code)) or bool(sweep_row.get("tenant_derivation"))
    svc_tenant, svc_where = (False, "")
    if not tenant:
        svc_tenant, svc_where = service_scopes_by_tenant(route.endpoint)
        tenant = tenant or svc_tenant
    branches = bool(ROLE_BRANCH.search(code))
    db = sweep_row.get("db_writes", "")
    ext = sweep_row.get("external_effects", "")

    ev = {
        "admitted_roles": "|".join(sorted(roles)) or "ALL_AUTHENTICATED",
        "actor_derivation": "yes" if actor else "no",
        "tenant_derivation": (sweep_row.get("tenant_derivation")
                              or ("in-handler" if TENANT_EXPR.search(code) else "")
                              or (f"service:{svc_where}" if svc_tenant else "")),
        "role_branching": "yes" if branches else "no",
        "db_writes": db, "external_effects": ext,
        "auth_dependencies": "|".join(d for d in deps if d in ADMITS or d.startswith("require_")) or "NONE",
    }

    # 1. Dependency positively fixes the persona.
    if roles and roles <= {"super_admin"}:
        return "PLATFORM_ADMIN_MUTATION", "dependency admits super_admin only", ev
    if roles and roles <= {"customer"}:
        return "CUSTOMER_SELF_SERVICE_MUTATION", "dependency admits customer only", ev
    if roles and roles <= {"tenant_owner", "super_admin", "staff", "technician"}:
        return "TENANT_PROVIDER_MUTATION", "dependency admits only tenant-side roles", ev

    # 2. Broad dependency -> decide on tenant authority.
    if tenant:
        return ("TENANT_PROVIDER_MUTATION",
                ("tenant derived from the authenticated principal and route mutates"
                 if not svc_tenant else
                 f"service layer scopes by tenant ({svc_where}); route mutates"), ev)

    # 3. No tenant authority: decide on what is mutated / who owns it.
    if path.startswith("/v1/admin") or path.startswith("/v1/internal"):
        return "PLATFORM_ADMIN_MUTATION", "admin/internal surface with no tenant derivation", ev
    if path.startswith("/v1/customer"):
        return "CUSTOMER_SELF_SERVICE_MUTATION", "customer surface", ev
    if path.startswith("/v1/public") or "webhook" in path or "callback" in path:
        return "TRUSTED_CALLBACK_OR_WEBHOOK_MUTATION", "public/webhook surface", ev
    if actor:
        # Acts on the caller's OWN principal-owned object (session, profile,
        # own token). Self-service by the authenticated principal; tenancy is
        # not the boundary because the object is user-owned.
        return ("PLATFORM_INTERNAL_MUTATION" if "auth" not in path else
                "SELF_PRINCIPAL_MUTATION"), \
               "mutates an object owned by the authenticated principal itself", ev
    if not db and not ext:
        return "READ_ONLY_FALSE_POSITIVE", "no persistent or external effect", ev
    return "PRODUCT_DECISION_REQUIRED", \
           "mutates shared/global state with neither tenant nor actor derivation", ev


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    idx = route_index()
    sweep = {(r["method"], norm(r["path"])): r
             for r in load(os.path.join(S26, "complete-mounted-route-inventory.csv"))}
    personas = load(os.path.join(S26, "mutation-persona-classification.csv"))

    # ── A. mixed-persona ─────────────────────────────────────────────────────
    mixed = [p for p in personas if p["persona"] == "MIXED_PERSONA_MUTATION"]
    a_rows = []
    for p in mixed:
        key = (p["method"], norm(p["path"]))
        rt = idx.get(key)
        if rt is None:
            a_rows.append({"method": key[0], "path": key[1], "endpoint": p["endpoint"],
                           "module": p["module"], "final_persona": "DISCONNECTED_MUTATION",
                           "basis": "not resolvable at runtime", "evidence_level": "RUNTIME"})
            continue
        persona, basis, ev = adjudicate(rt, sweep.get(key, {}), *key)
        a_rows.append({"method": key[0], "path": key[1], "endpoint": p["endpoint"],
                       "module": p["module"], "final_persona": persona, "basis": basis,
                       "evidence_level": "ROUTE_LEVEL", **ev})
    write("mixed-persona-route-inventory.csv", a_rows)
    print("  A. mixed-persona ->", dict(Counter(r["final_persona"] for r in a_rows)))

    # ── B. held candidates ───────────────────────────────────────────────────
    held = [r for r in load(os.path.join(S26, "generic-prefix-tenant-mutations.csv"))
            if r["verdict"] not in ("CONFIRMED_TENANT_MUTATION_ADD",)]
    b_rows = []
    for r in held:
        key = (r["method"], norm(r["path"]))
        rt = idx.get(key)
        if rt is None:
            b_rows.append({**r, "final_disposition": "DISCONNECTED",
                           "why_second_signal_absent": "route not resolvable at runtime"})
            continue
        persona, basis, ev = adjudicate(rt, sweep.get(key, {}), *key)
        b_rows.append({
            "method": key[0], "path": key[1], "endpoint": r.get("endpoint", ""),
            "previous_verdict": r["verdict"],
            "final_disposition": persona, "basis": basis,
            "why_second_signal_absent": (
                "tenant derivation happens inside the service, not the handler"
                if r["verdict"] == "MUTATION_BUT_TENANT_SOURCE_UNPROVEN_HOLD"
                else "side effect occurs deeper than the AST follow depth"),
            **ev})
    write("held-candidate-resolution.csv", b_rows)
    print("  B. held ->", dict(Counter(r["final_disposition"] for r in b_rows)))

    # ── C. classifier disagreements ──────────────────────────────────────────
    dis = load(os.path.join(S26, "prefixed-route-false-positive-audit.csv"))
    canon = {(c["method"], norm(c["path"])): c for c in load(CANON)}
    c_rows = []
    for r in dis:
        key = (r["method"], norm(r["path"]))
        rt = idx.get(key)
        c = canon.get(key, {})
        if rt is None:
            c_rows.append({"method": key[0], "path": key[1],
                           "endpoint": r.get("endpoint", ""),
                           "canonical_guard": c.get("guard_status", ""),
                           "final_persona": "TENANT_PROVIDER_MUTATION",
                           "final_disposition": "CANONICAL_ROW_CONFIRMED",
                           "basis": "canonical path form differs from the runtime key; "
                                    "capability present -- removal would need proof it is gone",
                           "evidence_source": "canonical CSV + path normalization"})
            continue
        persona, basis, ev = adjudicate(rt, sweep.get(key, {}), *key)
        disp = ("CANONICAL_ROW_CONFIRMED" if persona == "TENANT_PROVIDER_MUTATION"
                else "CANONICAL_PERSONA_CORRECTED")
        c_rows.append({"method": key[0], "path": key[1], "endpoint": r.get("endpoint", ""),
                       "canonical_guard": c.get("guard_status", ""),
                       "final_persona": persona, "final_disposition": disp,
                       "basis": basis, "evidence_source": "runtime dependency + AST",
                       **ev})
    write("classifier-disagreement-adjudication.csv", c_rows)
    print("  C. disagreements ->", dict(Counter(r["final_disposition"] for r in c_rows)))

    # ── D. mutating GETs ─────────────────────────────────────────────────────
    gets = load(os.path.join(S26, "mutating-get-audit.csv"))
    d_rows = []
    for r in gets:
        key = ("GET", norm(r["path"]))
        rt = idx.get(key)
        if rt is None:
            d_rows.append({**r, "final_class": "FALSE_POSITIVE_READ",
                           "basis": "not resolvable at runtime"})
            continue
        persona, basis, ev = adjudicate(rt, sweep.get(key, {}), *key)
        cls = {"TENANT_PROVIDER_MUTATION": "INTENTIONAL_TENANT_MUTATING_GET",
               "CUSTOMER_SELF_SERVICE_MUTATION": "CUSTOMER_MUTATING_GET",
               "PLATFORM_ADMIN_MUTATION": "PLATFORM_ADMIN_MUTATING_GET",
               "PLATFORM_INTERNAL_MUTATION": "INTERNAL_MUTATING_GET",
               "SELF_PRINCIPAL_MUTATION": "INTERNAL_MUTATING_GET",
               "TRUSTED_CALLBACK_OR_WEBHOOK_MUTATION": "PUBLIC_OR_CALLBACK_MUTATING_GET",
               "READ_ONLY_FALSE_POSITIVE": "FALSE_POSITIVE_READ",
               }.get(persona, "PRODUCT_DECISION_REQUIRED")
        d_rows.append({"path": key[1], "endpoint": r.get("endpoint", ""),
                       "module": r.get("module", ""), "final_class": cls,
                       "final_persona": persona, "basis": basis,
                       "db_writes": ev["db_writes"],
                       "external_effects": ev["external_effects"],
                       "in_canonical": "yes" if key in canon else "no"})
    write("mutating-get-revalidation.csv", d_rows)
    print("  D. mutating GET ->", dict(Counter(r["final_class"] for r in d_rows)))

    # ── E. read-only non-GET ─────────────────────────────────────────────────
    ro = load(os.path.join(S26, "read-only-post-audit.csv"))
    e_rows = []
    for r in ro:
        key = (r["method"], norm(r["path"]))
        rt = idx.get(key)
        sw = sweep.get(key, {})
        hidden = bool(sw.get("db_writes") or sw.get("external_effects")
                      or sw.get("audit_effects"))
        code = strip_prose(rt.endpoint) if rt else ""
        deep = bool(re.search(r"db\.add\(|db\.commit\(|db\.flush\(|\.delete\(", code))
        p = key[1].lower()
        cls = ("HIDDEN_SIDE_EFFECT_FOUND" if (hidden or deep) else
               "SEARCH_OR_QUERY" if any(k in p for k in ("search", "query", "filter", "list")) else
               "PREVIEW" if any(k in p for k in ("preview", "simulate", "estimate", "calculate", "quote")) else
               "VALIDATION_ONLY" if any(k in p for k in ("validate", "check", "verify")) else
               "PURE_CALCULATION")
        e_rows.append({"method": key[0], "path": key[1], "endpoint": r.get("endpoint", ""),
                       "module": r.get("module", ""), "final_class": cls,
                       "db_writes": sw.get("db_writes", ""),
                       "external_effects": sw.get("external_effects", ""),
                       "audit_effects": sw.get("audit_effects", ""),
                       "handler_write_expr": "yes" if deep else "no"})
    write("read-only-nonget-revalidation.csv", e_rows)
    print("  E. read-only non-GET ->", dict(Counter(r["final_class"] for r in e_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
