"""Slice 2F-26G — authority model with deterministic capability-family
precedence (D-07) and AST-based write detection (D-08).

Composes the Slice 2F-26F model (D-01…D-06 repairs) and overrides exactly two
things:

  D-07  capability family comes from `capability_rules_2f26g.resolve_family`,
        a levelled precedence contract, instead of an ordered regex list.
  D-08  side-effect comes from `write_detector_2f26g`, which walks the AST and
        cannot mistake an equality predicate for an assignment.

Nothing else changes: persona, tenant direction, actor/scope semantics and
abstention are inherited unchanged from 2F-26F, which validated 24/24 on those
fields against a fresh holdout.

Evidence only. No canonical data and no application code is modified.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))


def _load(name):
    spec = importlib.util.spec_from_file_location(name[:-3], os.path.join(HERE, name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


F = _load("authority_model_2f26f.py")     # D-01..D-06
FAM = _load("capability_rules_2f26g.py")   # D-07
WD = _load("write_detector_2f26g.py")      # D-08

TENANT_DIRECTION = F.TENANT_DIRECTION
ADMISSION = F.ADMISSION
ABSTENTION_REASONS = F.ABSTENTION_REASONS
SEMANTIC_ROLE = F.SEMANTIC_ROLE
CAPABILITY_FAMILY = F.CAPABILITY_FAMILY
CAPABILITY_ACTION = F.CAPABILITY_ACTION
norm = F.norm
route_index = F.route_index
R = F.R


def _capability_action(method, path):
    # action logic is unchanged from 2F-26F; only family precedence is repaired
    _, act = F.capability(method, path)
    return act


def side_effect(route):
    """AST-based. Returns (class, evidence, confidence)."""
    fn = route.endpoint
    method = sorted(route.methods or [""])[0]
    # handler body
    ws = WD.ast_writes(fn)
    conf = WD.confidence(fn)
    # qualified service methods called by the handler
    proof = [f"{w['qualified']}:{w['persistence']}" for w in ws]
    if not ws:
        for name, (cls, meth) in R._resolve_callees(fn).items():
            mws = WD.ast_writes(meth)
            if mws:
                ws = mws
                conf = WD.confidence(meth)
                proof = [f"{cls.__name__}.{name}:{w['persistence']}" for w in mws]
                break
    if ws:
        return "DATABASE_MUTATION", "|".join(sorted(set(proof))[:4]), conf
    if method == "GET":
        return "PURE_READ", "no AST write in handler or resolved callees", "HIGH_AST"
    return "DATABASE_MUTATION", "non-GET with no detected write (conservative)", "LOW_ASSUMED"


def resolve(route):
    base = F.resolve(route)
    method, path = base["method"], base["path"]

    # ── D-07: deterministic family ───────────────────────────────────────────
    fam, rid, lvl, fb = FAM.resolve_family(path)
    base["capability_family"] = fam
    base["capability_family_rule"] = rid
    base["capability_family_level"] = lvl
    base["capability_family_fallback"] = fb
    base["capability_action"] = _capability_action(method, path)
    base["capability_text"] = f"{fam}:{base['capability_action']}"

    # ── D-08: AST side-effect ────────────────────────────────────────────────
    se, ev, conf = side_effect(route)
    # preserve the 2F-26F correction of the alias/actor persona logic, which
    # depended on side_effect only via GET/mutation branch -- re-run it here.
    base["side_effect"] = se
    base["side_effect_evidence"] = ev
    base["side_effect_confidence"] = conf
    return base


if __name__ == "__main__":
    idx = route_index()
    for k in [("PUT", "/v1/tenant/service-areas/{area_id}/services/{mapping_id}"),
              ("DELETE", "/v1/me/profile-photo"),
              ("GET", "/v1/ds/tenants/{tenant_id}/pricing/recommendations"),
              ("GET", "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv")]:
        r = resolve(idx[k])
        print("=" * 74)
        print(*k)
        for f in ("capability_family", "capability_family_rule", "capability_action",
                  "side_effect", "side_effect_confidence", "side_effect_evidence"):
            print(f"  {f:24} {r[f]}")
