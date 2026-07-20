"""Slice 2F-26F — authority model with alias-aware tenant sourcing and
actor/subject/scope separation.

Extends the Slice 2F-26E unified record (which repaired D-01…D-04) with the
two defects the second holdout exposed:

  D-05  tenant sources are taken from the normalized, alias-aware request
        inventory -- the EXTERNAL request name, not the Python symbol.
  D-06  the principal's identity establishes scope only when it occupies a
        subject slot or participates in an ownership predicate; an actor or
        audit argument never does.

Also freezes the shared capability taxonomy (family + action) used by manual
sheets, classifier output, comparison logic and verifier fixtures.

Evidence only. No canonical data and no application code is modified.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))


def _load(name):
    spec = importlib.util.spec_from_file_location(name[:-3], os.path.join(HERE, name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


E = _load("authority_model_2f26e.py")     # D-01..D-04 repairs, taxonomy, guards
R = _load("request_model_2f26f.py")       # D-05/D-06 repairs

TENANT_DIRECTION = E.TENANT_DIRECTION
ADMISSION = E.ADMISSION
ABSTENTION_REASONS = E.ABSTENTION_REASONS
SEMANTIC_ROLE = R.SEMANTIC_ROLE
CAPABILITY_FAMILY = R.CAPABILITY_FAMILY
CAPABILITY_ACTION = R.CAPABILITY_ACTION
norm = E.norm
route_index = E.route_index
strip_prose = E.strip_prose

# ══════════════════════════════════════════════════════════════════════════
# WS4 — capability family/action derivation from the frozen taxonomy
# ══════════════════════════════════════════════════════════════════════════

_FAMILY_BY_PREFIX = [
    (r"^/v1/auth\b|^/v1/me\b", "identity_access"),
    (r"^/v1/tenants?\b", "tenant_governance"),
    (r"^/v1/staff\b|invite|^/v1/provider/staff", "staff_management"),
    (r"^/v1/customer\b", "customer_account"),
    (r"^/v1/bookings?\b|^/v1/appointments\b", "booking"),
    (r"^/v1/jobs?\b|^/v1/dispatch\b|^/v1/field-ops\b", "job_execution"),
    (r"^/v1/catalog\b|^/v1/services\b", "catalog"),
    (r"^/v1/pricing\b", "pricing"),
    (r"^/v1/packages?\b|^/v1/commerce\b", "package_commerce"),
    (r"^/v1/payments?\b|^/v1/invoices?\b|^/v1/billing\b", "billing"),
    (r"^/v1/reviews?\b|^/v1/reputation\b", "review_reputation"),
    (r"^/v1/notifications?\b|^/v1/chat\b", "notification"),
    (r"^/v1/compliance\b|^/v1/privacy\b", "compliance"),
    (r"^/v1/security\b|^/v1/audit\b", "security_audit"),
    (r"^/v1/analytics\b|^/v1/ds\b|^/v1/enterprise\b", "analytics"),
    (r"^/v1/marketing\b", "marketing"),
    (r"^/v1/webhooks?\b|^/v1/integrations?\b", "integration_webhook"),
    (r"^/v1/geo\b|^/v1/serviceability\b|^/v1/tenant/service-areas", "geography_serviceability"),
    (r"^/v1/media\b|^/v1/documents\b", "media"),
    (r"^/v1/inventory\b", "other"),
]

_ACTION_BY_TOKEN = [
    (r"/reset\b|/recalculate\b|/recompute\b", "recalculate"),
    (r"/resend\b", "resend"),
    (r"/revoke\b|/sessions/", "revoke"),
    (r"/rotate\b", "rotate"),
    (r"/confirm\b", "confirm"),
    (r"/cancel\b", "cancel"),
    (r"/approve\b", "approve"),
    (r"/reject\b", "reject"),
    (r"/activate\b|/enable\b|/reinstate\b|/set-primary\b", "activate"),
    (r"/deactivate\b|/disable\b|/suspend\b|/terminate\b", "deactivate"),
    (r"/export\b|/download\b", "export"),
    (r"/import\b|/ingest\b", "import"),
    (r"/preview\b", "preview"),
    (r"/dispatch\b|/compute\b|/execute\b|/release\b|/record\b", "execute"),
]


def capability(method, path):
    """(family, action). Both drawn from the frozen closed taxonomy."""
    fam = "other"
    for rx, f in _FAMILY_BY_PREFIX:
        if re.search(rx, path):
            fam = f
            break
    act = None
    for rx, a in _ACTION_BY_TOKEN:
        if re.search(rx, path):
            act = a
            break
    if act is None:
        act = {"POST": "create", "PUT": "update", "PATCH": "update",
               "DELETE": "delete", "GET": "other"}.get(method, "other")
    return fam, act


# ══════════════════════════════════════════════════════════════════════════
# The resolved record, alias-aware and actor/scope-separated
# ══════════════════════════════════════════════════════════════════════════

def resolve(route):
    base = E.resolve(route)
    fn = route.endpoint
    path = base["path"]
    method = base["method"]

    inputs = R.request_inputs(fn)
    tenants = R.tenant_inputs(fn, path)
    roles = R.value_roles(fn, path)
    own = R.ownership_evidence(fn)
    p_scope, p_reason = R.principal_is_scope(fn, path)

    fam, act = capability(method, path)
    base["capability_family"] = fam
    base["capability_action"] = act
    base["capability_text"] = f"{fam}:{act}"
    base["request_inputs"] = "|".join(
        f"{i['symbol']}->{i['external_name']}@{i['location']}" for i in inputs)
    base["aliased_inputs"] = "|".join(
        f"{i['symbol']}->{i['external_name']}" for i in inputs
        if i["symbol"] != i["external_name"])
    base["tenant_inputs"] = "|".join(
        f"{t['symbol']}->{t['external_name']}({t['alias_source']})" for t in tenants)
    base["semantic_roles"] = "|".join(sorted({r["role"] for r in roles}))
    base["actor_values"] = "|".join(
        r["value"] for r in roles if r["role"] == "ACTOR_IDENTITY")
    base["scope_evidence"] = "|".join(own) or "NONE"
    base["principal_is_scope"] = p_scope
    base["principal_scope_reason"] = p_reason

    # ── D-05: an aliased client tenant overrides the 26E direction ───────────
    guard_tenant = base["tenant_required_by_guard"] or base["access_scope_gated"]
    if tenants and not guard_tenant:
        if base["tenant_direction"] in (
                "NO_TENANT_AUTHORITY_REQUIRED", "REQUIRES_MANUAL_TENANT_ADJUDICATION",
                "OBJECT_DERIVED_TENANT"):
            base["tenant_direction"] = (
                "PLATFORM_ADMIN_TARGET_TENANT"
                if base["capability"] == "PLATFORM_ADMIN"
                else "CLIENT_ASSERTED_TARGET_TENANT")
            base["tenant_evidence"] = (
                "alias-aware request inventory found a client-supplied tenant: "
                + base["tenant_inputs"])
            if base["capability"] in ("ANY_AUTHENTICATED", "AMBIGUOUS"):
                base["capability"] = "TENANT_PROVIDER"
                base["persona"] = ("TENANT_PROVIDER_READ" if method == "GET"
                                   else "TENANT_PROVIDER_MUTATION")
                base["abstention_reason"] = ""

    # ── D-06: self-scope requires real scope evidence, not attribution ───────
    if base["tenant_direction"] == "NO_TENANT_AUTHORITY_REQUIRED" and not p_scope:
        if not tenants and not guard_tenant:
            base["tenant_direction"] = "REQUIRES_MANUAL_TENANT_ADJUDICATION"
            base["tenant_evidence"] = (
                f"principal identity is attribution only ({p_reason}); "
                f"no ownership predicate establishes scope")
            base["persona"] = "REQUIRES_MANUAL_ADJUDICATION"
            base["abstention_reason"] = "OWNERSHIP_CHECK_IN_SERVICE_NOT_TRACEABLE"
    return base


if __name__ == "__main__":
    idx = route_index()
    for k in [("POST", "/v1/commerce/warranty/claims"),
              ("POST", "/v1/auth/staff/{user_id}/invite/resend"),
              ("DELETE", "/v1/auth/sessions/{session_id}")]:
        r = resolve(idx[k])
        print("=" * 76)
        print(*k)
        for f in ("capability", "capability_family", "capability_action", "persona",
                  "tenant_direction", "tenant_inputs", "semantic_roles",
                  "scope_evidence", "principal_is_scope"):
            print(f"  {f:22} {r[f]}")
