"""Slice 2F-27 — two methodologically-distinct adjudication streams.

HONESTY NOTE (carried into every artifact): this slice is executed by a SINGLE
agent. Reviewer A and Reviewer B are two DIFFERENT automated adjudication
methodologies with different primary evidence and no shared verdict state --
they are NOT two independent human reviewers. Genuine two-human independence
cannot be established by one agent, and this file does not pretend otherwise.
The streams share low-level helpers (guard resolution, AST parsing); that
shared substrate is disclosed, not hidden.

  REVIEWER_A  persistence-first: decide side-effect from the AST write
              detector, then persona from side-effect + admitted-role set,
              reading ownership predicates from source.

  REVIEWER_B  authority-first: decide persona from the resolved guard chain and
              alias-aware request-input tenant semantics, then side-effect.

Both emit the frozen shared taxonomies only. Neither sees the other's verdict
or the classifier verdict at decision time.
"""
from __future__ import annotations

import importlib.util
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))


def _load(name):
    spec = importlib.util.spec_from_file_location(name[:-3], os.path.join(HERE, name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


H = _load("authority_model_2f26h.py")     # composed model (shared substrate)
FAM = _load("capability_rules_2f26g.py")
WD = _load("write_detector_2f26g.py")
ACT = _load("action_model_2f26h.py")
R = H.R
norm = H.norm
route_index = H.route_index

PLATFORM_ADMIN = {"super_admin", "admin_operations", "admin_finance",
                  "admin_security", "admin_readonly"}
TENANT_SIDE = {"tenant_owner", "staff", "technician"}


def _guard_roles(route):
    guards = H.G.F.E.route_guards(route)
    static, _ = H.G.F.E.admitted_roles(guards)
    runtime_ext = any(g["runtime_extensible"] for g in guards)
    tenant_guard = any(g["tenant_required"] for g in guards)
    return static, runtime_ext, tenant_guard


# ══════════════════════════════════════════════════════════════════════════
# REVIEWER A — persistence-first
# ══════════════════════════════════════════════════════════════════════════

def reviewer_a(route):
    method = sorted(route.methods or ["?"])[0]
    path = norm(route.path)
    fn = route.endpoint

    # 1. side-effect from AST first
    se, ev, conf = H.G.side_effect(route)
    if method == "GET":
        behavior = "MUTATING_GET" if se == "DATABASE_MUTATION" else "READ_ONLY"
    else:
        behavior = "DATABASE_MUTATION" if se == "DATABASE_MUTATION" else "READ_ONLY"

    # 2. persona from behavior + roles + ownership
    static, runtime_ext, tenant_guard = _guard_roles(route)
    own = R.ownership_evidence(fn)
    p_scope, _ = R.principal_is_scope(fn, path)
    tenants = R.tenant_inputs(fn, path)
    self_scoped = p_scope

    if behavior in ("READ_ONLY",):
        persona = "READ_ONLY_NOT_MUTATION"
    elif static is not None and static and static <= PLATFORM_ADMIN and not runtime_ext:
        persona = "PLATFORM_ADMIN_MUTATION"
    elif static is not None and static and static <= {"customer"}:
        persona = "CUSTOMER_SELF_SERVICE_MUTATION"
    elif tenant_guard or tenants:
        persona = "TENANT_PROVIDER_MUTATION"
    elif self_scoped and not tenants:
        persona = "SELF_SERVICE_MUTATION"
    else:
        persona = "PRODUCT_DECISION_REQUIRED" if not own else "TENANT_PROVIDER_MUTATION"

    # tenant direction
    if tenant_guard:
        direction = "PRINCIPAL_TENANT"
    elif tenants:
        direction = "CLIENT_ASSERTED_TARGET_TENANT"
    elif self_scoped:
        direction = "NO_TENANT_AUTHORITY_REQUIRED"
    else:
        direction = "REQUIRES_MANUAL_TENANT_ADJUDICATION"

    return {"behavior": behavior, "persona": persona, "tenant_direction": direction,
            "capability_family": FAM.resolve_family(path)[0],
            "side_effect": se, "evidence": ev or (own and own[0]) or "roles=" + (
                "|".join(sorted(static)) if static else "?")}


# ══════════════════════════════════════════════════════════════════════════
# REVIEWER B — authority-first
# ══════════════════════════════════════════════════════════════════════════

def reviewer_b(route):
    method = sorted(route.methods or ["?"])[0]
    path = norm(route.path)
    fn = route.endpoint

    # 1. persona from guard chain + request-input authority first
    static, runtime_ext, tenant_guard = _guard_roles(route)
    tenants = R.tenant_inputs(fn, path)
    p_scope, p_reason = R.principal_is_scope(fn, path)

    if static is not None and static and static <= PLATFORM_ADMIN and not runtime_ext:
        cap = "PLATFORM_ADMIN"
    elif static is not None and static and static <= {"customer"}:
        cap = "CUSTOMER"
    elif tenant_guard:
        cap = "TENANT_PROVIDER"
    elif runtime_ext and (tenants or H.G.F.E._tenant_subject(path)):
        cap = "TENANT_PROVIDER"
    elif p_scope:
        cap = "SELF"
    else:
        cap = "AMBIGUOUS"

    # 2. side-effect second
    se, ev, conf = H.G.side_effect(route)
    if method == "GET":
        behavior = "MUTATING_GET" if se == "DATABASE_MUTATION" else "READ_ONLY"
    else:
        behavior = "DATABASE_MUTATION" if se == "DATABASE_MUTATION" else "READ_ONLY"

    persona = {
        "PLATFORM_ADMIN": "PLATFORM_ADMIN_MUTATION",
        "CUSTOMER": "CUSTOMER_SELF_SERVICE_MUTATION",
        "TENANT_PROVIDER": "TENANT_PROVIDER_MUTATION",
        "SELF": "SELF_SERVICE_MUTATION",
        "AMBIGUOUS": "PRODUCT_DECISION_REQUIRED",
    }[cap]
    if behavior == "READ_ONLY":
        persona = "READ_ONLY_NOT_MUTATION"

    if tenant_guard:
        direction = "PRINCIPAL_TENANT"
    elif tenants:
        direction = "CLIENT_ASSERTED_TARGET_TENANT"
    elif p_scope:
        direction = "NO_TENANT_AUTHORITY_REQUIRED"
    elif cap == "TENANT_PROVIDER":
        direction = "OBJECT_DERIVED_TENANT"
    else:
        direction = "REQUIRES_MANUAL_TENANT_ADJUDICATION"

    return {"behavior": behavior, "persona": persona, "tenant_direction": direction,
            "capability_family": FAM.resolve_family(path)[0],
            "side_effect": se,
            "evidence": f"cap={cap};roles={'|'.join(sorted(static)) if static else '?'};"
                        f"tenant_guard={tenant_guard};tenants={bool(tenants)}"}


if __name__ == "__main__":
    idx = route_index()
    k = ("POST", "/v1/tenants/{tenant_id}/engines/bulk-disable")
    print("A:", reviewer_a(idx[k]))
    print("B:", reviewer_b(idx[k]))
