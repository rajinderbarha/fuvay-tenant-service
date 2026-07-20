"""Slice 2F-26H — authority model with tokenized capability-action inference.

Composes the Slice 2F-26G model (D-01…D-08 repairs) and overrides exactly one
thing: capability_action now comes from `action_model_2f26h.infer_action`,
which tokenizes the path, endpoint and qualified service-method names, maps
verbs through a documented synonym table, and never lets POST default to
`create`.

Everything else — persona, tenant direction, capability family, side effect,
actor/scope semantics, abstention — is inherited unchanged from 2F-26G, which
validated those fields at 24/24 on a fresh holdout.

Evidence only. No canonical data and no application code is modified.
"""
from __future__ import annotations

import importlib.util
import inspect
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


G = _load("authority_model_2f26g.py")     # D-01..D-08
ACT = _load("action_model_2f26h.py")       # D-09

TENANT_DIRECTION = G.TENANT_DIRECTION
ADMISSION = G.ADMISSION
ABSTENTION_REASONS = G.ABSTENTION_REASONS
SEMANTIC_ROLE = G.SEMANTIC_ROLE
CAPABILITY_FAMILY = G.CAPABILITY_FAMILY
CAPABILITY_ACTION = ACT.ACTIONS
norm = G.norm
route_index = G.route_index
R = G.F.R


def _service_method_names(fn):
    """Qualified service methods actually called by this handler."""
    return list(R._resolve_callees(fn).keys())


def resolve(route):
    base = G.resolve(route)
    fn = route.endpoint
    method, path = base["method"], base["path"]

    svc = _service_method_names(fn)
    has_write = base["side_effect"] == "DATABASE_MUTATION"
    act = ACT.infer_action(method=method, path=path,
                           endpoint_name=getattr(fn, "__name__", ""),
                           service_methods=svc, has_proven_write=has_write)
    base["capability_action"] = act["action"]
    base["action_source"] = act["source"]
    base["action_confidence"] = act["confidence"]
    base["action_tokens"] = "|".join(act["tokens"])
    base["action_rejected"] = act["rejected"]
    base["action_conflict"] = act["conflict"]
    base["capability_text"] = f"{base['capability_family']}:{act['action']}"
    return base


if __name__ == "__main__":
    idx = route_index()
    for k in [("POST", "/v1/tenants/{tenant_id}/engines/bulk-disable"),
              ("POST", "/v1/tenants/{tenant_id}/engines/bulk-enable"),
              ("POST", "/v1/chat/conversations"),
              ("DELETE", "/v1/media/{media_id}")]:
        r = resolve(idx[k])
        print(f"{k[0]:6} {k[1][:44]:44} action={r['capability_action']:12} "
              f"({r['action_source']})")
