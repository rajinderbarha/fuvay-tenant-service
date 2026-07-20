"""Slice 2F-26E — unified resolved-authority model.

ONE resolved representation consumed by persona assignment, tenant-authority
inference, branch adjudication, canonical-inclusion logic, the protection
classifier and the standalone verifier. Slice 2F-26D failed because role
resolution and `tenant_authority()` were separate models that could disagree;
they are the same record here.

Repairs the four confirmed defects:

  D-01  Runtime-extensible StaffPermission semantics are now CONSUMED by
        persona assignment. `require_permission(P.X)` calls
        `permission_checker.has(..., overrides=user.permission_overrides)`,
        so a permission absent from ROLE_PERMISSIONS is NOT super-admin-only
        -- any principal carrying a matching StaffPermission grant is
        admitted. Admission is modelled as an ADMISSION_* value, never as a
        bare role set.

  D-02  Tenant direction is inferred from the SAME resolved guard record as
        persona. The decisive signal the old model discarded: guards in the
        `*_mutation` family run a tenant read-only access_scope gate, which is
        a tenant-side concept -- such a guard establishes PRINCIPAL_TENANT by
        construction, whatever the handler body looks like.

  D-03  One frozen closed taxonomy (`TENANT_DIRECTION`), shared by manual
        sheets, classifier output and verifier fixtures.

  D-04  Abstention is emitted only with a precise reason code, and only for
        causes that are genuinely unresolvable from available evidence.

Produces evidence only. Nothing here edits canonical data.
"""
from __future__ import annotations

import ast
import functools
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ══════════════════════════════════════════════════════════════════════════
# WS3 — the frozen shared tenant-direction taxonomy
# ══════════════════════════════════════════════════════════════════════════

TENANT_DIRECTION = {
    "PRINCIPAL_TENANT":
        "Tenant is the authenticated principal's own tenant, established by the "
        "guard or derived from the principal in the handler.",
    "OBJECT_DERIVED_TENANT":
        "Tenant is carried by the target object row, addressed by its own id.",
    "PARENT_DERIVED_TENANT":
        "Tenant is derived from a parent record named in the request.",
    "CUSTOMER_RELATIONSHIP_TENANT":
        "Tenant follows from the customer's relationship to the tenant.",
    "PLATFORM_ADMIN_TARGET_TENANT":
        "A platform-admin principal acts UPON a tenant named in the request.",
    "CLIENT_ASSERTED_TARGET_TENANT":
        "Tenant identifier supplied by the client and used without comparison "
        "against the principal's own tenant.",
    "OPTIONAL_FILTER_TENANT":
        "Tenant narrows a result set but confers no authority.",
    "CALLBACK_PAYLOAD_TENANT":
        "Tenant arrives inside a trusted callback payload.",
    "INTERNAL_CONTEXT_TENANT":
        "Tenant supplied by an internal caller's context, not an end user.",
    "GLOBAL_PLATFORM_SCOPE":
        "Route operates across the platform; no single tenant applies.",
    "NO_TENANT_AUTHORITY_REQUIRED":
        "Route is self-scoped or tenant-independent; tenant confers no authority.",
    "REQUIRES_MANUAL_TENANT_ADJUDICATION":
        "Direction is not determinable from available evidence.",
}

# `NO_TENANT_SCOPE`, used by the 2F-26D manual sheet, is deliberately NOT a
# member. Its intended meaning splits across NO_TENANT_AUTHORITY_REQUIRED
# (self-scoped) and OBJECT_DERIVED_TENANT (tenant-owned object addressed by
# id). Collapsing those was defect D-03.

ADMISSION = {
    "STATIC_ROLES", "TENANT_STAFF_OVERRIDE_ELIGIBLE",
    "STATIC_AND_RUNTIME_EXTENSIBLE", "PLATFORM_ADMIN_ONLY",
    "REQUIRES_MANUAL_CAPABILITY_ADJUDICATION",
}

PERSONA = {
    "TENANT_PROVIDER_MUTATION", "CUSTOMER_SELF_SERVICE_MUTATION",
    "PLATFORM_ADMIN_MUTATION", "PLATFORM_INTERNAL_MUTATION",
    "PUBLIC_OR_UNAUTHENTICATED_MUTATION", "TRUSTED_CALLBACK_MUTATION",
    "SELF_SERVICE_MUTATION", "TENANT_PROVIDER_READ", "SELF_SERVICE_READ",
    "PLATFORM_ADMIN_READ", "REQUIRES_MANUAL_ADJUDICATION",
}

# WS5 — the only permitted abstention causes.
ABSTENTION_REASONS = {
    "DYNAMIC_SERVICE_DISPATCH_UNRESOLVED",
    "OWNERSHIP_CHECK_IN_SERVICE_NOT_TRACEABLE",
    "RUNTIME_BRANCH_DEPENDS_ON_UNAVAILABLE_STATE",
    "PRODUCT_POLICY_UNRESOLVED",
    "MULTIPLE_MUTATING_BRANCHES_INCOMPLETE_EVIDENCE",
}

# ══════════════════════════════════════════════════════════════════════════
# Canonical role sets
# ══════════════════════════════════════════════════════════════════════════

ALL_AUTHENTICATED = {"super_admin", "tenant_owner", "staff", "technician",
                     "customer", "admin_operations", "admin_finance",
                     "admin_security", "admin_readonly"}
BASE_ROLES = {
    "get_current_user": ALL_AUTHENTICATED,
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

# Guards that establish the principal's OWN tenant by construction. Every
# member runs the tenant read-only access_scope gate, which only makes sense
# for a tenant-side principal. This is the D-02 repair.
TENANT_SCOPED_GUARDS = {
    "require_tenant_owner_mutation", "require_owner_or_office_staff_mutation",
    "require_tenant_mutation_permission", "require_technician",
    "require_tenant_owner", "require_staff_or_technician_only",
}

PRINCIPAL_TENANT_EXPR = re.compile(
    r"\b(user|u|actor|principal|current_user)\.tenant_id\b|_tid\(|_tenant_id\(|"
    r"_effective_tenant\(|actor_tenant_id")
PRINCIPAL_SELF_EXPR = re.compile(
    r"\b(user|u|actor|principal|current_user)\.user_id\b")
WRITE = re.compile(
    r"\bdb\.(add|delete|flush|commit|add_all|merge)\(|\bself\.db\.(add|delete|flush|commit)\(|"
    r"\bsession\.(add|delete|flush|commit)\(|\.status\s*=|\.deleted_at\s*=|"
    r"\.archived_at\s*=|\.is_active\s*=")


def norm(p):
    return p if p.startswith("/v1/") else ("/v1" + p if p.startswith("/") else p)


def _dedent(s):
    ls = s.splitlines()
    if not ls:
        return s
    i = len(ls[0]) - len(ls[0].lstrip())
    return "\n".join(l[i:] if len(l) >= i else l for l in ls)


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


# ══════════════════════════════════════════════════════════════════════════
# Guard resolution (unchanged semantics from 2F-26B, single source here)
# ══════════════════════════════════════════════════════════════════════════

def roles_from_inline_check(fn):
    try:
        tree = ast.parse(_dedent(inspect.getsource(fn)))
    except Exception:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Attribute) and node.left.attr == "role"):
            continue
        for cmp in node.comparators:
            if isinstance(cmp, (ast.Tuple, ast.List, ast.Set)):
                vals = {e.value for e in cmp.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)}
                if vals:
                    return vals
            if isinstance(cmp, ast.Name):
                mod = sys.modules.get(getattr(fn, "__module__", ""))
                const = getattr(mod, cmp.id, None) if mod else None
                if isinstance(const, (set, tuple, list, frozenset)):
                    vals = {v for v in const if isinstance(v, str)}
                    if vals:
                        return vals
    return None


def static_roles_for_permission(perm: str):
    """Roles admitted by ROLE_PERMISSIONS alone -- the STATIC half only."""
    if not perm:
        return None
    try:
        from app.core.permissions import ROLE_PERMISSIONS, P
    except Exception:
        return None
    engine = perm.split(":")[0] if ":" in perm else perm.split(".")[0]
    out = {"super_admin"}
    for r, perms in ROLE_PERMISSIONS.items():
        if r == "super_admin" or getattr(P, "ALL", "*") in perms or perm in perms:
            out.add(r)
        elif f"{engine}:*" in perms or f"{engine}.*" in perms:
            out.add(r)
    return out


def permission_in_static_map(perm: str) -> bool:
    try:
        from app.core.permissions import ROLE_PERMISSIONS
    except Exception:
        return False
    return any(perm in v for v in ROLE_PERMISSIONS.values())


_PERM_REVERSE = None


def permission_from_name(name: str):
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
    chain, seen, cur = [], set(), fn
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
            cells = getattr(cur, "__closure__", None) or ()
            cand = [c.cell_contents for c in cells
                    if callable(getattr(c, "cell_contents", None))]
            nxt = cand[0] if cand else None
        cur = nxt
        depth += 1
    return fn, chain, any(c in BASE_ROLES for c in chain)


def closure_permission(fn):
    for c in getattr(fn, "__closure__", None) or ():
        v = getattr(c, "cell_contents", None)
        if isinstance(v, str) and len(v) < 80 and (v.isupper() or "." in v or "_" in v):
            return v
        if callable(v):
            r = closure_permission(v)
            if r:
                return r
    return ""


def _guard_family(symbol, chain, permission):
    """Which factory produced this guard. Drives tenant requirement."""
    src = " ".join(chain) + " " + symbol
    if "require_tenant_mutation_permission" in src:
        return "require_tenant_mutation_permission"
    for g in TENANT_SCOPED_GUARDS:
        if g in src:
            return g
    if symbol in BASE_ROLES:
        return symbol
    if permission or symbol.startswith("require_"):
        return "require_permission"
    return "unknown"


def route_guards(route):
    """Every authorization callable on a route, fully resolved, with the
    runtime-extensibility and tenant-requirement facts attached."""
    out = []
    d = getattr(route, "dependant", None)

    def rec(x):
        c = getattr(x, "call", None)
        if c is not None and callable(c):
            nm = getattr(c, "__name__", "")
            if nm.startswith("require_") or nm in BASE_ROLES or nm == "_check":
                final, chain, ok = unwrap(c)
                perm = closure_permission(c) or permission_from_name(nm)
                # tenant-mutation factories are recognised by their module-level
                # source, since the produced callable is named for its permission
                try:
                    fsrc = inspect.getsource(inspect.unwrap(c))
                except Exception:
                    fsrc = ""
                if "TENANT_READONLY_ACCESS_SCOPES" in fsrc:
                    chain = chain + ["require_tenant_mutation_permission"]
                family = _guard_family(nm, chain, perm)

                static, inline = None, None
                if ok:
                    static = BASE_ROLES.get(getattr(final, "__name__", ""), None)
                if static is None:
                    inline = roles_from_inline_check(final)
                    static = inline
                if static is None and (perm or nm.startswith("require_")):
                    static = static_roles_for_permission(perm or nm[len("require_"):])

                # ── D-01: runtime extensibility is a first-class fact ──────────
                runtime_ext = bool(perm) or family in (
                    "require_permission", "require_tenant_mutation_permission")
                in_map = permission_in_static_map(perm) if perm else False
                if runtime_ext and not in_map:
                    admission = ("STATIC_AND_RUNTIME_EXTENSIBLE"
                                 if family == "require_tenant_mutation_permission"
                                 else "TENANT_STAFF_OVERRIDE_ELIGIBLE")
                elif runtime_ext:
                    admission = "STATIC_AND_RUNTIME_EXTENSIBLE"
                elif static is not None:
                    admission = ("PLATFORM_ADMIN_ONLY"
                                 if static and static <= PLATFORM_ADMIN else "STATIC_ROLES")
                else:
                    admission = "REQUIRES_MANUAL_CAPABILITY_ADJUDICATION"

                out.append({
                    "symbol": nm,
                    "family": family,
                    "resolved_to": getattr(final, "__name__", "?"),
                    "chain": "->".join(chain),
                    "resolved": bool(ok or static is not None),
                    "permission": perm,
                    "permission_in_static_map": in_map,
                    "static_roles": "|".join(sorted(static)) if static else "",
                    "admission": admission,
                    "runtime_extensible": runtime_ext,
                    "tenant_required": family in TENANT_SCOPED_GUARDS,
                    "access_scope_gated": "TENANT_READONLY_ACCESS_SCOPES" in fsrc,
                    "module": getattr(c, "__module__", ""),
                })
        for s in getattr(x, "dependencies", []) or []:
            rec(s)
    if d:
        rec(d)
    return out


def admitted_roles(guards):
    """Intersection of resolved static role sets. Unresolved -> None."""
    sets = []
    for g in guards:
        if g["static_roles"]:
            sets.append(set(g["static_roles"].split("|")))
        elif not g["resolved"]:
            return None, f"unresolved guard: {g['symbol']} ({g['chain']})"
    if not sets:
        return set(), "no role-restricting guard"
    r = set.intersection(*sets) if len(sets) > 1 else sets[0]
    return r, "resolved"


# ══════════════════════════════════════════════════════════════════════════
# WS1 — the unified resolved-authority record
# ══════════════════════════════════════════════════════════════════════════

def _param_names(fn):
    try:
        return set(inspect.signature(fn).parameters)
    except Exception:
        return set()


def resolve(route):
    """The single record every downstream consumer reads."""
    path = norm(route.path)
    fn = route.endpoint
    guards = route_guards(route)
    static, rnote = admitted_roles(guards)
    code = strip_prose(fn)
    params = _param_names(fn)

    tenant_guard = any(g["tenant_required"] for g in guards)
    scope_gated = any(g["access_scope_gated"] for g in guards)
    runtime_ext = any(g["runtime_extensible"] for g in guards)
    admissions = {g["admission"] for g in guards}

    path_tenant = "{tenant_id}" in path
    param_tenant = "tenant_id" in params
    # Must match tenant_id ARRIVING FROM THE REQUEST only. A bare `.tenant_id`
    # also matches `job.tenant_id` -- an OBJECT-derived tenant, the opposite of
    # a client-asserted one. That over-match mis-classified the enterprise
    # export download as a tenant route in burned-sample regression.
    body_tenant = bool(re.search(
        r"body\[[\"']tenant_id[\"']\]|body\.get\(\s*[\"']tenant_id|\bbody\.tenant_id\b",
        code)) and not path_tenant
    principal_tenant = bool(PRINCIPAL_TENANT_EXPR.search(code))
    self_scoped = bool(PRINCIPAL_SELF_EXPR.search(code))
    platform_only = static is not None and bool(static) and static <= PLATFORM_ADMIN

    # A platform-admin conclusion is only TRUSTED when the permission is
    # actually present in ROLE_PERMISSIONS. When it is absent, the static set
    # collapses to {super_admin} as an artefact of the map, not as a fact about
    # the route -- concluding "platform admin" from that artefact is defect
    # D-01. When it IS present, admin_finance et al. are genuinely the
    # admitted set and the conclusion stands.
    perm_in_map = any(g["permission_in_static_map"] for g in guards if g["permission"])
    platform_only_trusted = platform_only and (not runtime_ext or perm_in_map)

    # ── WS2/WS4: capability, from the SAME record ────────────────────────────
    if tenant_guard or scope_gated:
        capability = "TENANT_PROVIDER"
    elif platform_only_trusted:
        capability = "PLATFORM_ADMIN"
    elif static is not None and static and static <= {"customer"}:
        capability = "CUSTOMER"
    elif runtime_ext:
        # D-01: absent from ROLE_PERMISSIONS does NOT mean super-admin-only.
        # A tenant-side principal with a StaffPermission grant is admitted, so
        # capability follows the ROUTE's subject, not the static role set.
        capability = "TENANT_PROVIDER" if (
            path_tenant or param_tenant or body_tenant or principal_tenant
            or _tenant_subject(path)) else "AMBIGUOUS"
    elif static is not None and static == ALL_AUTHENTICATED:
        capability = "ANY_AUTHENTICATED"
    else:
        capability = "AMBIGUOUS"

    direction, evidence = _direction(
        capability, tenant_guard, scope_gated, platform_only_trusted, runtime_ext,
        path_tenant, param_tenant, body_tenant, principal_tenant, self_scoped, path)

    persona, abstain = _persona(route, capability, direction, static,
                                platform_only_trusted, self_scoped, runtime_ext)

    return {
        "method": sorted(route.methods or ["?"])[0],
        "path": path,
        "endpoint": getattr(fn, "__name__", ""),
        "module": getattr(fn, "__module__", ""),
        "guard_symbols": "|".join(sorted({g["symbol"] for g in guards})) or "NONE",
        "guard_family": "|".join(sorted({g["family"] for g in guards})) or "NONE",
        "static_roles": "|".join(sorted(static)) if static else "",
        "admission": ("REQUIRES_MANUAL_CAPABILITY_ADJUDICATION"
                      if "REQUIRES_MANUAL_CAPABILITY_ADJUDICATION" in admissions
                      else ("STATIC_AND_RUNTIME_EXTENSIBLE"
                            if "STATIC_AND_RUNTIME_EXTENSIBLE" in admissions
                            else ("TENANT_STAFF_OVERRIDE_ELIGIBLE"
                                  if "TENANT_STAFF_OVERRIDE_ELIGIBLE" in admissions
                                  else ("PLATFORM_ADMIN_ONLY" if platform_only
                                        else "STATIC_ROLES")))),
        "runtime_extensible": runtime_ext,
        "permission": "|".join(sorted({g["permission"] for g in guards if g["permission"]})),
        "tenant_required_by_guard": tenant_guard,
        "access_scope_gated": scope_gated,
        "capability": capability,
        "tenant_direction": direction,
        "tenant_evidence": evidence,
        "persona": persona,
        "abstention_reason": abstain,
        "side_effect": "DATABASE_MUTATION" if WRITE.search(code) or _service_writes(fn)
                       else ("PURE_READ" if sorted(route.methods or [""])[0] == "GET"
                             else "DATABASE_MUTATION"),
        "resolved": all(g["resolved"] for g in guards) if guards else True,
        "note": rnote,
    }


_TENANT_SUBJECT = re.compile(
    r"^/v1/(tenant|tenants|provider|staff|media|pricing|geo|inventory|documents|"
    r"appointments|webhooks|field-ops|compliance|serviceability)\b")


def _tenant_subject(path):
    return bool(_TENANT_SUBJECT.match(path))


def _direction(capability, tenant_guard, scope_gated, platform_only, runtime_ext,
               path_tenant, param_tenant, body_tenant, principal_tenant,
               self_scoped, path):
    """D-02 repair: consumes the resolved guard record, not a separate model."""
    # 1. The guard itself establishes the principal's own tenant.
    if tenant_guard or scope_gated:
        return ("PRINCIPAL_TENANT",
                "guard runs the tenant read-only access_scope gate, which "
                "presupposes a tenant-side principal")
    # 2. Handler derives tenant from the authenticated principal.
    if principal_tenant:
        return "PRINCIPAL_TENANT", "handler derives tenant from the principal"
    # 3. Platform admin acting upon a named tenant.
    if platform_only:
        return ("PLATFORM_ADMIN_TARGET_TENANT" if (path_tenant or param_tenant)
                else "GLOBAL_PLATFORM_SCOPE",
                "platform-admin-only guard")
    # 4. Tenant named by the client, never compared to the principal's.
    if path_tenant or param_tenant or body_tenant:
        return ("CLIENT_ASSERTED_TARGET_TENANT",
                "tenant identifier supplied by the request with no principal comparison")
    # 5. Self-scoped: authority comes from identity, not tenancy.
    if self_scoped:
        return ("NO_TENANT_AUTHORITY_REQUIRED",
                "handler scopes to the principal's own user_id")
    # 6. Tenant-owned object addressed by its own id.
    if capability == "TENANT_PROVIDER":
        return ("OBJECT_DERIVED_TENANT",
                "tenant carried by the target object row, addressed by id")
    return ("REQUIRES_MANUAL_TENANT_ADJUDICATION",
            "no tenant value identified from guard or handler dataflow")


def _service_writes(fn):
    """Qualified: service class from annotation or module import, method body."""
    mod = sys.modules.get(getattr(fn, "__module__", ""))
    code = strip_prose(fn)
    called = set(re.findall(r"\.(\w+)\(", code))
    cands = []
    try:
        for _, p in inspect.signature(fn).parameters.items():
            if inspect.isclass(p.annotation):
                cands.append(p.annotation)
    except Exception:
        pass
    if mod:
        for n in dir(mod):
            o = getattr(mod, n, None)
            if inspect.isclass(o) and n.endswith(("Service", "Manager")):
                cands.append(o)
    seen = set()
    for cls in cands:
        if id(cls) in seen:
            continue
        seen.add(id(cls))
        for mname, meth in inspect.getmembers(cls, inspect.isfunction):
            if mname in called and WRITE.search(strip_prose(meth)):
                return True
    return False


def _persona(route, capability, direction, static, platform_only, self_scoped,
             runtime_ext):
    """Persona from CAPABILITY and AUTHORITY -- not from potential role admission
    alone. That distinction is the D-01 repair."""
    is_read = sorted(route.methods or [""])[0] == "GET"
    if capability == "TENANT_PROVIDER":
        return ("TENANT_PROVIDER_READ" if is_read else "TENANT_PROVIDER_MUTATION"), ""
    if capability == "PLATFORM_ADMIN":
        return ("PLATFORM_ADMIN_READ" if is_read else "PLATFORM_ADMIN_MUTATION"), ""
    if capability == "CUSTOMER":
        return "CUSTOMER_SELF_SERVICE_MUTATION", ""
    if capability == "ANY_AUTHENTICATED":
        if direction == "NO_TENANT_AUTHORITY_REQUIRED":
            return ("SELF_SERVICE_READ" if is_read else "SELF_SERVICE_MUTATION"), ""
        if direction == "CLIENT_ASSERTED_TARGET_TENANT":
            # authority is asserted by the client; the route's subject is a tenant
            return ("TENANT_PROVIDER_READ" if is_read else "TENANT_PROVIDER_MUTATION"), ""
    return ("REQUIRES_MANUAL_ADJUDICATION",
            "OWNERSHIP_CHECK_IN_SERVICE_NOT_TRACEABLE")


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


if __name__ == "__main__":
    idx = route_index()
    print(f"{len(idx)} mounted routes")
    from collections import Counter
    recs = [resolve(rt) for rt in list(idx.values())[:400]]
    print("capability:", dict(Counter(r["capability"] for r in recs)))
    print("direction :", dict(Counter(r["tenant_direction"] for r in recs)))
