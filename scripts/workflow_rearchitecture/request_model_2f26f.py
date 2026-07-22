"""Slice 2F-26F — alias-aware request-field model and semantic value-role dataflow.

Repairs the two defects the second holdout exposed:

  D-05  FastAPI/Pydantic parameter aliases were invisible. The scan looked for
        a parameter *named* `tenant_id`; `tid: UUID = Query(..., alias="tenant_id")`
        is named `tid`, so a client-asserted tenant was missed entirely.
        FIX: every request input is normalized to BOTH its Python symbol and
        its external request name, from Query/Path/Header/Cookie/Form/File
        defaults, Annotated metadata, and Pydantic Field alias /
        validation_alias / serialization_alias / AliasChoices / AliasPath.

  D-06  Actor identity was read as ownership scope. `user.user_id` passed as
        an audit/actor argument was treated as proof the target is
        self-scoped.
        FIX: arguments are mapped POSITIONALLY onto the resolved callee's
        parameter names, so `resend_invite(user_id, actor)` is seen for what
        it is -- the principal lands in an actor slot, and the path `user_id`
        is the target subject. Scope requires an ownership predicate, never
        attribution.

Evidence only. Nothing here edits canonical data or application code.
"""
from __future__ import annotations

import ast
import inspect
import os
import re
import sys
import typing

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ══════════════════════════════════════════════════════════════════════════
# WS2 — closed semantic value-role taxonomy
# ══════════════════════════════════════════════════════════════════════════

SEMANTIC_ROLE = {
    "PRINCIPAL_IDENTITY": "The authenticated principal's own identity.",
    "PRINCIPAL_TENANT": "The authenticated principal's own tenant.",
    "ACTOR_IDENTITY": "Who performed the action, used for attribution.",
    "AUDIT_ACTOR_IDENTITY": "Actor recorded specifically on an audit/history row.",
    "TARGET_USER": "The user the action is performed upon.",
    "TARGET_CUSTOMER": "The customer the action is performed upon.",
    "TARGET_PROVIDER": "The provider the action is performed upon.",
    "TARGET_TENANT": "The tenant the action is performed upon.",
    "OBJECT_IDENTITY": "The object being acted upon, addressed by its own id.",
    "PARENT_IDENTITY": "A parent record named in the request.",
    "OBJECT_DERIVED_TENANT": "Tenant carried by the target object row.",
    "PARENT_DERIVED_TENANT": "Tenant derived from a parent record.",
    "CUSTOMER_RELATIONSHIP_TENANT": "Tenant via the customer relationship.",
    "CLIENT_ASSERTED_TENANT": "Tenant named by the client, uncompared.",
    "OPTIONAL_FILTER": "Narrows results; confers no authority.",
    "CALLBACK_SUBJECT": "Subject inside a trusted callback payload.",
    "STATE_INPUT": "A state/status value supplied by the request.",
    "FINANCIAL_INPUT": "A monetary amount supplied by the request.",
    "NON_AUTHORIZATION_METADATA": "Carries no authorization meaning.",
    "REQUIRES_MANUAL_SEMANTIC_ADJUDICATION": "Not determinable from evidence.",
}

# WS4 — closed capability taxonomy
CAPABILITY_FAMILY = {
    "identity_access", "tenant_governance", "staff_management", "customer_account",
    "booking", "job_execution", "catalog", "pricing", "package_commerce", "billing",
    "review_reputation", "notification", "compliance", "security_audit",
    "analytics", "marketing", "integration_webhook", "geography_serviceability",
    "media", "other",
}
CAPABILITY_ACTION = {
    "create", "update", "delete", "activate", "deactivate", "approve", "reject",
    "confirm", "cancel", "resend", "rotate", "revoke", "recalculate", "export",
    "import", "preview", "execute", "other",
}

# ── WS3: what makes a value SCOPE, and what explicitly does not ─────────────

# Callee parameter names that mean "who did this", never "what may they touch".
ACTOR_PARAM_NAMES = {
    "actor_id", "actor", "actor_user_id", "audit_actor_id", "created_by",
    "updated_by", "requested_by", "performed_by", "changed_by", "by_user",
    "by_user_id", "sender_id", "notification_sender", "history_actor",
    "event_actor", "reported_by", "issued_by", "approved_by", "uploaded_by",
    "resolved_by", "assigned_by", "invited_by", "revoked_by", "inviter_id",
    "inviter", "actor_user", "audit_actor", "creator_id",
}
# Callee parameter names that identify the SUBJECT being acted upon.
SUBJECT_PARAM_NAMES = {
    "user_id", "target_user_id", "customer_id", "provider_id", "staff_id",
    "technician_id", "subject_id", "owner_id", "member_id",
    # common abbreviations -- the external/alias repair applies here too
    "uid", "cid", "sid",
}
TENANT_PARAM_NAMES = {"tenant_id", "tid", "target_tenant_id", "org_id"}

# Evidence that a value genuinely participates in authorization scope.
OWNERSHIP_PREDICATE = re.compile(
    r"\.where\([^)]*==|\.filter\([^)]*==|\.filter_by\(|"
    r"if\s+\w+\.(owner_id|user_id|customer_id|tenant_id|staff_id)\s*!=|"
    r"_assert_own|_assert_owner|_get_\w*scoped|scoped\(|"
    r"raise\s+\w*(PermissionDenied|Forbidden)", re.I)


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
# WS1 — normalized, alias-aware request-input inventory
# ══════════════════════════════════════════════════════════════════════════

def _alias_from_fastapi_default(default):
    """Query/Path/Header/Cookie/Form/File carry `.alias`."""
    for attr in ("alias", "validation_alias", "serialization_alias"):
        v = getattr(default, attr, None)
        if isinstance(v, str) and v:
            return v, attr
    return None, None


def _pydantic_fields(model, prefix=""):
    """Every field of a Pydantic model, following nested models, alias-aware."""
    out = []
    fields = getattr(model, "model_fields", None)
    if not fields:
        return out
    for name, f in fields.items():
        ext = name
        src = "name"
        for attr in ("alias", "validation_alias", "serialization_alias"):
            v = getattr(f, attr, None)
            if isinstance(v, str) and v:
                ext, src = v, attr
                break
            # AliasChoices / AliasPath
            choices = getattr(v, "choices", None)
            if choices:
                first = next((c for c in choices if isinstance(c, str)), None)
                if first:
                    ext, src = first, f"{attr}:AliasChoices"
                    break
            pth = getattr(v, "path", None)
            if pth:
                ext, src = ".".join(str(x) for x in pth), f"{attr}:AliasPath"
                break
        ann = getattr(f, "annotation", None)
        out.append({"symbol": name, "external_name": ext, "location": "body",
                    "alias_source": src, "model_path": prefix + name,
                    "type": getattr(ann, "__name__", str(ann)),
                    "required": bool(getattr(f, "is_required", lambda: False)()),
                    "client_controlled": True})
        if hasattr(ann, "model_fields"):
            out.extend(_pydantic_fields(ann, prefix + name + "."))
    return out


def request_inputs(fn):
    """Normalized inventory of every client-controlled input of a handler.

    Records the Python symbol AND the external request name separately. The
    external name is what a client actually sends; conflating the two was
    defect D-05.
    """
    out = []
    try:
        sig = inspect.signature(fn)
        hints = typing.get_type_hints(fn, include_extras=True)
    except Exception:
        return out
    for name, p in sig.parameters.items():
        ann = hints.get(name, p.annotation)
        loc, ext, src = "path_or_query", name, "name"

        # Annotated[..., Query(alias=...)] metadata
        meta = getattr(ann, "__metadata__", ()) if hasattr(ann, "__metadata__") else ()
        base = getattr(ann, "__origin__", ann) if meta else ann
        for m in meta:
            a, s = _alias_from_fastapi_default(m)
            if a:
                ext, src = a, f"Annotated:{s}"
            loc = type(m).__name__.lower() or loc

        d = p.default
        if d is not inspect.Parameter.empty and d is not None:
            a, s = _alias_from_fastapi_default(d)
            if a:
                ext, src = a, f"{type(d).__name__}:{s}"
            tn = type(d).__name__
            if tn in ("Query", "Path", "Header", "Cookie", "Form", "File", "Body"):
                loc = tn.lower()
            if tn == "Depends":
                loc = "depends"

        tname = getattr(base, "__name__", str(base))
        if tname in ("Request", "AsyncSession", "UserContext") or loc == "depends":
            continue
        if hasattr(base, "model_fields"):
            out.extend(_pydantic_fields(base, prefix=f"{name}."))
            continue
        out.append({"symbol": name, "external_name": ext, "location": loc,
                    "alias_source": src, "model_path": name, "type": tname,
                    "required": d is inspect.Parameter.empty,
                    "client_controlled": True})
    return out


def tenant_inputs(fn, path=""):
    """Client-controlled inputs that carry a TENANT, by external name.

    D-05 repair: matches the EXTERNAL request name, so an aliased `tid` is
    found. Guards against the inverse error -- a name merely containing
    'tenant' in prose (e.g. `tenant_note`) is not a tenant identifier.
    """
    hits = []
    for i in request_inputs(fn):
        for nm in (i["external_name"], i["symbol"]):
            if nm in TENANT_PARAM_NAMES or nm.endswith("_tenant_id"):
                hits.append(i)
                break
    if "{tenant_id}" in path and not any(h["location"] == "path" for h in hits):
        hits.append({"symbol": "tenant_id", "external_name": "tenant_id",
                     "location": "path", "alias_source": "path_template",
                     "model_path": "tenant_id", "type": "UUID",
                     "required": True, "client_controlled": True})
    return hits


# ══════════════════════════════════════════════════════════════════════════
# WS2/WS3 — value-role dataflow with actor/subject/scope separation
# ══════════════════════════════════════════════════════════════════════════

def _resolve_callees(fn):
    """(callee_name -> function) for qualified service calls in this handler."""
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
    out, seen = {}, set()
    for cls in cands:
        if id(cls) in seen:
            continue
        seen.add(id(cls))
        for mn, me in inspect.getmembers(cls, inspect.isfunction):
            if mn in called and mn not in out:
                out[mn] = (cls, me)
    return out


def _arg_text(node):
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def value_roles(fn, path=""):
    """Map each request value and the principal onto a semantic role.

    The core of the D-06 repair: handler call arguments are mapped
    POSITIONALLY onto the resolved callee's parameter names, so a principal
    landing in an `actor_id` slot is attribution, and a path id landing in a
    `user_id` slot is the target subject.
    """
    roles = []
    code = strip_prose(fn)
    callees = _resolve_callees(fn)
    tenants = {t["external_name"] for t in tenant_inputs(fn, path)}
    tsyms = {t["symbol"] for t in tenant_inputs(fn, path)}

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return roles

    principal_slots, subject_slots, tenant_slots = [], [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = node.func.attr if isinstance(node.func, ast.Attribute) else None
        if fname not in callees:
            continue
        cls, meth = callees[fname]
        try:
            params = [p for p in inspect.signature(meth).parameters if p != "self"]
        except Exception:
            continue
        for i, arg in enumerate(node.args):
            if i >= len(params):
                break
            pname, atext = params[i], _arg_text(arg)
            is_principal = bool(re.search(
                r"\b(user|u|actor|principal|current_user)\.user_id\b", atext))
            if is_principal:
                (principal_slots).append((fname, pname, atext))
            if any(t in atext for t in (tsyms | tenants)):
                tenant_slots.append((fname, pname, atext))
            if pname in SUBJECT_PARAM_NAMES and not is_principal:
                subject_slots.append((fname, pname, atext))
        for kw in node.keywords:
            atext = _arg_text(kw.value)
            if re.search(r"\b(user|u|actor|principal|current_user)\.user_id\b", atext):
                principal_slots.append((fname, kw.arg or "", atext))

    # ── principal identity: actor attribution vs genuine subject ────────────
    for fname, pname, atext in principal_slots:
        if pname in ACTOR_PARAM_NAMES:
            roles.append({"value": atext, "role": "ACTOR_IDENTITY",
                          "evidence": f"passed to {fname}(...) as `{pname}` -- an "
                                      f"attribution slot, not a scope slot",
                          "scope_relevant": False})
        elif pname in SUBJECT_PARAM_NAMES:
            roles.append({"value": atext, "role": "PRINCIPAL_IDENTITY",
                          "evidence": f"passed to {fname}(...) as `{pname}` -- the "
                                      f"principal IS the subject (self-service)",
                          "scope_relevant": True})
        else:
            roles.append({"value": atext, "role": "ACTOR_IDENTITY",
                          "evidence": f"passed to {fname}(...) as `{pname}`; no "
                                      f"ownership predicate observed",
                          "scope_relevant": False})

    for fname, pname, atext in subject_slots:
        roles.append({"value": atext, "role": "TARGET_USER",
                      "evidence": f"request value in {fname}(...) slot `{pname}`",
                      "scope_relevant": False})

    for fname, pname, atext in tenant_slots:
        roles.append({"value": atext, "role": "CLIENT_ASSERTED_TENANT",
                      "evidence": f"client-supplied tenant into {fname}(...) `{pname}`",
                      "scope_relevant": True})

    return roles


def ownership_evidence(fn):
    """Explicit evidence that SOME ownership/scope check exists.

    Searched in the handler and in every resolved callee body. Absence is
    reported as absence -- never silently treated as 'protected'.
    """
    ev = []
    code = strip_prose(fn)
    if OWNERSHIP_PREDICATE.search(code):
        ev.append("handler-level ownership predicate")
    for name, (cls, meth) in _resolve_callees(fn).items():
        src = strip_prose(meth)
        if OWNERSHIP_PREDICATE.search(src):
            ev.append(f"{cls.__name__}.{name}: ownership predicate")
    return ev


def principal_is_scope(fn, path=""):
    """D-06: does the principal's identity actually establish scope?

    True only when the principal lands in a SUBJECT slot or participates in an
    ownership predicate. An actor/audit argument never qualifies.
    """
    rs = value_roles(fn, path)
    if any(r["role"] == "PRINCIPAL_IDENTITY" and r["scope_relevant"] for r in rs):
        return True, "principal occupies the subject slot"
    if not any(r["role"] in ("ACTOR_IDENTITY", "PRINCIPAL_IDENTITY") for r in rs):
        return False, "principal identity not passed to any resolved callee"
    if ownership_evidence(fn):
        return True, "ownership predicate present"
    return False, "principal identity used for attribution only"


if __name__ == "__main__":
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "am", os.path.join(os.path.dirname(__file__), "authority_model_2f26e.py"))
    A = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(A)
    idx = A.route_index()
    for k in [("POST", "/v1/commerce/warranty/claims"),
              ("POST", "/v1/auth/staff/{user_id}/invite/resend")]:
        rt = idx[k]
        print("=" * 78)
        print(*k)
        print(" tenant inputs:", [(t["symbol"], t["external_name"], t["alias_source"])
                                  for t in tenant_inputs(rt.endpoint, k[1])])
        for r in value_roles(rt.endpoint, k[1]):
            print(f"   {r['role']:22} scope={r['scope_relevant']}  {r['evidence']}")
        print(" ownership:", ownership_evidence(rt.endpoint) or "NONE FOUND")
        print(" principal_is_scope:", principal_is_scope(rt.endpoint, k[1]))
