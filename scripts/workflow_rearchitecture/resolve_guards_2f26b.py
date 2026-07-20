"""Slice 2F-26B — guard-alias resolution and principal-vs-target tenant dataflow.

Fixes the two blockers that invalidated the 2F-26A adjudicator:

  BLOCKER 1  "references tenant_id" was treated as "scoped to the caller's
             tenant". For a route acting UPON a tenant named in the path
             (`POST /v1/tenants/{tenant_id}/suspend`, super-admin) the
             inference is inverted.
             FIX: classify the tenant VALUE by where it comes from --
             PRINCIPAL_TENANT vs PLATFORM_ADMIN_TARGET_TENANT vs
             CLIENT_ASSERTED_TENANT -- never by symbol presence.

  BLOCKER 2  Router-local guard aliases (`_provider_guard =
             require_owner_or_office_staff_mutation`) were unknown to the
             static map, so role resolution silently degraded to the
             `get_current_user` superset.
             FIX: resolve the actual dependency CALLABLE from the live route
             object, unwrap closures/partials/wrappers, and fail closed on
             anything unresolved.

Nothing here edits canonical data. It produces evidence only.
"""
from __future__ import annotations

import ast
import csv
import functools
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26b")

# Canonical role sets, read from app/dependencies/auth.py + app/core/permissions.py.
BASE_ROLES = {
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
TENANT_SIDE = {"tenant_owner", "staff", "technician"}
PLATFORM_ADMIN = {"super_admin", "admin_operations", "admin_finance",
                  "admin_security", "admin_readonly"}

PRINCIPAL_TENANT_EXPR = re.compile(
    r"\b(user|u|actor|principal|current_user)\.tenant_id\b|_tid\(|_tenant_id\(|"
    r"_effective_tenant\(|actor_tenant_id")


def norm(p):
    return p if p.startswith("/v1/") else ("/v1" + p if p.startswith("/") else p)


def roles_from_inline_check(fn):
    """Pattern B: a real named guard with an inline role tuple.

    e.g. `require_owner_or_office_staff_mutation` contains
    `if user.role not in ("super_admin", "tenant_owner", "staff"): raise`.
    The admitted set is that tuple. Extracted from the AST, not from the name.
    """
    try:
        tree = ast.parse(_dedent(inspect.getsource(fn)))
    except Exception:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        if not (isinstance(left, ast.Attribute) and left.attr == "role"):
            continue
        for cmp in node.comparators:
            if isinstance(cmp, (ast.Tuple, ast.List, ast.Set)):
                vals = {e.value for e in cmp.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)}
                if vals:
                    return vals
            if isinstance(cmp, ast.Name):
                # role set held in a module constant -- resolve it live
                mod = sys.modules.get(getattr(fn, "__module__", ""))
                const = getattr(mod, cmp.id, None) if mod else None
                if isinstance(const, (set, tuple, list, frozenset)):
                    vals = {v for v in const if isinstance(v, str)}
                    if vals:
                        return vals
    return None


def roles_from_permission(perm: str):
    """Pattern A: factory guard. Admitted roles = roles the checker would grant.

    Mirrors `PermissionChecker.has` resolution order:
      super_admin always | role wildcard `*` | exact match | engine wildcard.

    NOT modelled: per-user StaffPermission overrides, which can widen the set
    at RUNTIME for staff principals. A permission absent from the map therefore
    resolves to {super_admin} *statically*, and the caller records confidence
    as STATIC_ONLY_RUNTIME_EXTENSIBLE rather than claiming a complete set.
    """
    if not perm:
        return None
    try:
        from app.core.permissions import ROLE_PERMISSIONS, P
    except Exception:
        return None
    engine = perm.split(":")[0] if ":" in perm else perm.split(".")[0]
    out = set()
    for r, perms in ROLE_PERMISSIONS.items():
        if r == "super_admin" or getattr(P, "ALL", "*") in perms or perm in perms:
            out.add(r); continue
        if f"{engine}:*" in perms or f"{engine}.*" in perms:
            out.add(r)
    out.add("super_admin")
    return out or None


_PERM_REVERSE = None


def permission_from_name(name: str):
    """Exact reverse of the factory naming convention.

    `_check.__name__ = f"require_{permission.replace(':', '_')}"`, so build a
    reverse index from the ACTUAL permission set rather than guessing where the
    separators were. Guessing failed on three-segment permissions
    (`admin:jobs:read`) and on permissions that use dots
    (`marketing.automation.read`), which contain no colons at all.
    """
    global _PERM_REVERSE
    if _PERM_REVERSE is None:
        try:
            from app.core.permissions import ROLE_PERMISSIONS
            _PERM_REVERSE = {}
            for perms in ROLE_PERMISSIONS.values():
                for perm in perms:
                    _PERM_REVERSE[perm.replace(":", "_")] = perm
                    _PERM_REVERSE[perm] = perm
        except Exception:
            _PERM_REVERSE = {}
    if not name.startswith("require_"):
        return ""
    body = name[len("require_"):]
    for pref in ("tenant_mutation_", "any_"):
        if body.startswith(pref):
            body = body[len(pref):]
    return _PERM_REVERSE.get(body, "")


def unwrap(fn, depth=0):
    """Follow wrappers, partials and closures to the real guard.

    Returns (final_callable, chain_description, resolved_flag).
    """
    chain = []
    seen = set()
    cur = fn
    while cur is not None and depth < 12:
        name = getattr(cur, "__name__", repr(cur))
        if id(cur) in seen:
            break
        seen.add(id(cur))
        chain.append(name)
        if name in BASE_ROLES:
            return cur, chain, True
        nxt = getattr(cur, "__wrapped__", None)
        if nxt is None and isinstance(cur, functools.partial):
            nxt = cur.func
        if nxt is None:
            # closure cells: require_permission(P.X) -> _check closing over role_check
            cells = getattr(cur, "__closure__", None) or ()
            cand = [c.cell_contents for c in cells
                    if callable(getattr(c, "cell_contents", None))]
            nxt = cand[0] if cand else None
        cur = nxt
        depth += 1
    return fn, chain, any(c in BASE_ROLES for c in chain)


def closure_permission(fn):
    """Extract the permission string a require_permission factory closed over."""
    for c in getattr(fn, "__closure__", None) or ():
        v = getattr(c, "cell_contents", None)
        if isinstance(v, str) and (v.isupper() or "." in v or "_" in v):
            if len(v) < 80:
                return v
        if callable(v):
            r = closure_permission(v)
            if r:
                return r
    return ""


def route_guards(route):
    """Every authorization callable on a route, fully resolved.

    Covers endpoint params, router-level and app-level dependencies, because
    FastAPI flattens them all into `route.dependant`.
    """
    out = []
    d = getattr(route, "dependant", None)

    def rec(x):
        c = getattr(x, "call", None)
        if c is not None and callable(c):
            nm = getattr(c, "__name__", "")
            if nm.startswith("require_") or nm in BASE_ROLES or nm == "_check":
                final, chain, ok = unwrap(c)
                perm = closure_permission(c) or permission_from_name(nm)
                rr, conf = None, "EXACT"
                if not ok:
                    rr = roles_from_inline_check(final)
                    if rr:
                        conf = "AST_INLINE_ROLE_SET"
                    else:
                        # a require_* factory guard: resolve via the checker
                        if nm.startswith("require_"):
                            perm2 = perm or nm[len("require_"):]
                            rr = roles_from_permission(perm2)
                            conf = ("PERMISSION_MAP" if perm else
                                    "STATIC_ONLY_RUNTIME_EXTENSIBLE")
                    if rr:
                        ok = True
                out.append({
                    "roles_resolved": "|".join(sorted(rr)) if rr else "",
                    "confidence": conf,
                    "symbol": nm,
                    "resolved_to": getattr(final, "__name__", "?"),
                    "chain": "->".join(chain),
                    "resolved": ok,
                    "permission": perm,
                    "module": getattr(c, "__module__", ""),
                })
        for s in getattr(x, "dependencies", []) or []:
            rec(s)
    if d:
        rec(d)
    return out


def admitted_roles(guards):
    """Intersection of resolved role sets. UNRESOLVED -> None (fail closed)."""
    sets = []
    for g in guards:
        if g["resolved_to"] in BASE_ROLES:
            sets.append(BASE_ROLES[g["resolved_to"]])
        elif g["symbol"] in BASE_ROLES:
            sets.append(BASE_ROLES[g["symbol"]])
        elif g.get("roles_resolved"):
            sets.append(set(g["roles_resolved"].split("|")))
        elif not g["resolved"]:
            return None, f"unresolved guard: {g['symbol']} ({g['chain']})"
    if not sets:
        return set(), "no role-restricting guard"
    r = set.intersection(*sets) if len(sets) > 1 else sets[0]
    return r, "resolved"


def strip_prose(fn):
    try:
        src = inspect.getsource(fn)
    except Exception:
        return ""
    try:
        t = ast.parse(_dedent(src))
    except SyntaxError:
        return src
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                          ast.Module)) and ast.get_docstring(n):
            n.body = n.body[1:]
    try:
        return ast.unparse(t)
    except Exception:
        return src


def _dedent(s):
    ls = s.splitlines()
    if not ls:
        return s
    i = len(ls[0]) - len(ls[0].lstrip())
    return "\n".join(l[i:] if len(l) >= i else l for l in ls)


def tenant_authority(route, guards, roles):
    """BLOCKER 1 FIX — classify the tenant value by ORIGIN, not by presence.

    Returns (classification, evidence).
    """
    path = norm(route.path)
    code = strip_prose(route.endpoint)
    sig = inspect.signature(route.endpoint)
    path_tenant = "{tenant_id}" in path or "tenant_id" in sig.parameters
    principal_tenant = bool(PRINCIPAL_TENANT_EXPR.search(code))

    if principal_tenant:
        return "PRINCIPAL_TENANT", "handler derives tenant from the authenticated principal"
    if roles is not None and roles and roles <= PLATFORM_ADMIN:
        if path_tenant:
            return ("PLATFORM_ADMIN_TARGET_TENANT",
                    "platform-admin-only guard acting upon a tenant named in the request")
        return "PLATFORM_ADMIN_TARGET_TENANT", "platform-admin-only guard"
    if path_tenant:
        return ("CLIENT_ASSERTED_TENANT",
                "tenant identifier supplied by the request with no principal comparison")
    return "UNKNOWN_TENANT_ROLE", "no tenant value identified"


def classify(route):
    guards = route_guards(route)
    roles, rnote = admitted_roles(guards)
    if roles is None:
        return {"persona": "UNRESOLVED_FAIL_CLOSED", "roles": "", "note": rnote,
                "tenant_authority": "UNKNOWN_TENANT_ROLE", "guards": guards}
    ta, tnote = tenant_authority(route, guards, roles)

    if roles and roles <= PLATFORM_ADMIN:
        persona = "PLATFORM_ADMIN_MUTATION"
    elif roles and roles <= {"customer"}:
        persona = "CUSTOMER_SELF_SERVICE_MUTATION"
    elif roles and roles <= (TENANT_SIDE | {"super_admin"}):
        persona = "TENANT_PROVIDER_MUTATION"
    elif ta == "PRINCIPAL_TENANT":
        persona = "TENANT_PROVIDER_MUTATION"
    elif ta == "PLATFORM_ADMIN_TARGET_TENANT":
        persona = "PLATFORM_ADMIN_MUTATION"
    else:
        persona = "REQUIRES_MANUAL_ADJUDICATION"
    return {"persona": persona, "roles": "|".join(sorted(roles)) or "ALL_AUTHENTICATED",
            "note": f"{rnote}; {tnote}", "tenant_authority": ta, "guards": guards}


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


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    idx = route_index()
    print(f"resolved {len(idx)} mounted (method, path) keys")

    # ── WS1: symbol inventory ────────────────────────────────────────────────
    symbols = {}
    for key, rt in idx.items():
        for g in route_guards(rt):
            s = symbols.setdefault(g["symbol"], {
                "symbol": g["symbol"], "resolved_to": g["resolved_to"],
                "chain": g["chain"], "resolved": g["resolved"],
                "permission": g["permission"], "module": g["module"],
                "confidence": g.get("confidence", ""),
                "canonical_roles": (g.get("roles_resolved") or "|".join(sorted(
                    BASE_ROLES.get(g["resolved_to"], BASE_ROLES.get(g["symbol"], set()))))),
                "consumers": 0})
            s["consumers"] += 1
    rows = sorted(symbols.values(), key=lambda r: -r["consumers"])
    with open(os.path.join(OUT, "authorization-symbol-inventory.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    unresolved = [r for r in rows if not r["resolved"]]
    print(f"  {len(rows)} guard symbols; {len(unresolved)} unresolved")
    for r in unresolved[:10]:
        print(f"    UNRESOLVED {r['symbol']} chain={r['chain']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
