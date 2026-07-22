"""Slice 2F-26H — tokenized capability-action inference (D-09 repair).

Slice 2F-26G matched actions with slash-anchored regexes (`/disable\\b`). The
path segment `bulk-disable` is hyphen-joined, so `/disable` did not match and
the route fell through to the POST default `create`. `bulk-disable` is a
`deactivate`.

This module:

  WS2  tokenizes the path, endpoint function name and qualified service method
       name -- splitting on `/`, `-`, `_` and CamelCase boundaries.
  WS3  maps normalized verbs to the frozen action taxonomy via a DOCUMENTED
       synonym table, never by silent lexical similarity.
  WS4  resolves action through an explicit precedence:
         1 explicit route override
         2 established service/state-machine operation
         3 qualified service method verb
         4 endpoint function verb
         5 tokenized path verb
         6 strong HTTP fallback (DELETE->delete; PUT/PATCH+proven write->update)
         7 REQUIRES_MANUAL_ACTION_ADJUDICATION
       POST never auto-means create.
  WS5  fails closed when two strong sources map to different actions.

Evidence only. No canonical data and no application code is modified.
"""
from __future__ import annotations

import re

# ── The frozen action taxonomy (unchanged from 2F-26F) ──────────────────────
ACTIONS = {
    "create", "update", "delete", "activate", "deactivate", "approve", "reject",
    "confirm", "cancel", "resend", "rotate", "revoke", "recalculate", "export",
    "import", "preview", "execute", "other",
}

MANUAL = "REQUIRES_MANUAL_ACTION_ADJUDICATION"

# ── WS3: documented verb -> action synonym mapping ──────────────────────────
# Each entry is an explicit, reviewed decision, not an automatic synonym.
VERB_TO_ACTION = {
    # create family
    "create": "create", "add": "create", "register": "create", "provision": "create",
    "new": "create", "initiate": "create", "submit": "create", "generate": "create",
    "hold": "create", "reserve": "create", "issue": "create", "open": "create",
    # update family
    "update": "update", "edit": "update", "patch": "update", "change": "update",
    "set": "update", "modify": "update", "configure": "update", "config": "update",
    # delete family
    "delete": "delete", "remove": "delete", "purge": "delete", "destroy": "delete",
    # activate
    "enable": "activate", "activate": "activate", "reinstate": "activate",
    "reenable": "activate", "publish": "activate",
    # deactivate  (see NOTE below on suspend/terminate)
    "disable": "deactivate", "deactivate": "deactivate", "suspend": "deactivate",
    "terminate": "deactivate",
    # approve / reject / confirm / cancel
    "approve": "approve", "accept": "approve",
    "reject": "reject", "decline": "reject",
    "confirm": "confirm", "verify": "confirm",
    "cancel": "cancel", "abort": "cancel",
    # resend / rotate / revoke
    "resend": "resend", "retry": "resend",
    "rotate": "rotate", "regenerate": "rotate",
    "revoke": "revoke", "invalidate": "revoke", "logout": "revoke",
    # recalculate / export / import / preview / execute
    "recalculate": "recalculate", "recompute": "recalculate",
    "export": "export", "download": "export",
    "import": "import", "ingest": "import", "upload": "import",
    "preview": "preview", "estimate": "preview", "simulate": "preview",
    "execute": "execute", "run": "execute", "trigger": "execute",
    "dispatch": "execute", "apply": "execute", "compute": "execute",
    "reassign": "execute", "assign": "execute",
    "downgrade": "update", "upgrade": "update",   # plan changes = update
}

# NOTE (WS3): suspend/terminate/deactivate. The frozen taxonomy has a single
# `deactivate` action; the tenant state machine distinguishes suspend from
# terminate as separate business operations, but at the CAPABILITY-ACTION
# granularity they are all `deactivate`. This is a documented, deliberate
# collapse -- the taxonomy has no finer value -- not an invented equivalence.
# Where a route needs the finer distinction it belongs in mutated_resource /
# capability_text, not in the action enum.

# Words that are NOUNS/identifiers here, never action verbs (WS2 exclusion).
NOUN_STOPWORDS = {
    "bulk", "all", "me", "my", "self", "api", "key", "keys", "session", "sessions",
    "user", "users", "staff", "tenant", "tenants", "job", "jobs", "engine", "engines",
    "rule", "rules", "zone", "zones", "item", "items", "invoice", "invoices",
    "payment", "payments", "order", "orders", "customer", "customers", "media",
    "document", "documents", "consent", "badge", "badges", "channel", "channels",
    "webhook", "webhooks", "endpoint", "endpoints", "profile", "photo", "reservation",
    "reservations", "conversation", "conversations", "knowledge", "base", "bases",
    "kb", "signed", "token", "settings", "setting", "brand",
    "adjustment", "wallet", "purchase", "warranty", "claim", "claims", "location",
    "forecast", "recommendations", "factors", "score", "ltv", "demand", "churn",
    "imports",
    "pricing", "prices", "price", "plan", "trial", "data", "billing", "method",
    "notifications", "notification", "deletion", "requests", "request", "events",
    "activity", "audit", "log", "mfa", "setup", "login", "history", "column",
    "preferences", "primary", "mapping", "services", "areas", "area", "feature",
    "flags", "flag", "chat", "orders",
}
# `export`/`import` deliberately excluded from stopwords as verbs handled via
# VERB_TO_ACTION when they head a segment; but as nouns (exports/{id}) they are
# stopped. We keep them stopworded and rely on explicit path-verb position.

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def tokenize(text):
    """Normalized token sequence. Splits /, -, _ and CamelCase; lowercases."""
    if not text:
        return []
    text = _CAMEL.sub(" ", text)
    parts = re.split(r"[/\-_.\s]+", text)
    out = []
    for p in parts:
        p = p.strip().lower()
        if not p or p.startswith("{"):        # skip path params like {tenant_id}
            continue
        out.append(p)
    return out


def _leading_verb(tokens):
    """The operation verb of a verb-first function/method name.

    Skip leading noun stopwords, then the FIRST meaningful token decides: if it
    is a known verb, use it; otherwise return None. This stops a noun that
    merely resembles a verb deeper in the name from being read as the action --
    `get_export_job` -> None (the head is `get`, a read helper, not `export`),
    while `bulk_disable_engines` -> disable (skip the `bulk` stopword) and
    `confirm_hold` -> confirm (hold is the trailing object)."""
    for t in tokens:
        if t in NOUN_STOPWORDS:
            continue
        return (t, VERB_TO_ACTION[t]) if t in VERB_TO_ACTION else None
    return None


def _trailing_verb(tokens):
    """The action verb of a REST path: the LAST non-parameter segment that is a
    known verb. `/engines/bulk-disable` -> disable; `/api-keys/{id}/rotate` ->
    rotate. Resource nouns in earlier segments are ignored."""
    for t in reversed(tokens):
        if t in VERB_TO_ACTION and t not in NOUN_STOPWORDS:
            return (t, VERB_TO_ACTION[t])
    return None


def infer_action(*, method, path, endpoint_name="", service_methods=(),
                 override=None, has_proven_write=False):
    """Deterministic action with full evidence. Returns a dict.

    keys: action, source, confidence, tokens, rejected, conflict
    """
    path_tokens = tokenize(path)
    fn_tokens = tokenize(endpoint_name)
    svc_tokens = [t for m in service_methods for t in tokenize(m)]

    evidence = []   # (precedence_level, source, action)

    # 0 reads carry no mutation action
    if method == "GET":
        return {"action": "other", "source": "http_get_read", "confidence": "HTTP_STRONG",
                "tokens": path_tokens, "rejected": "", "conflict": ""}

    # 1 explicit override
    if override in ACTIONS:
        return {"action": override, "source": "route_override", "confidence": "EXPLICIT",
                "tokens": path_tokens, "rejected": "", "conflict": ""}

    # 3 qualified service method verb (leading verb per method)
    for m in service_methods:
        v = _leading_verb(tokenize(m))
        if v:
            evidence.append((3, f"service_method:{v[0]}", v[1]))
    # 4 endpoint function verb (leading verb)
    v = _leading_verb(fn_tokens)
    if v:
        evidence.append((4, f"endpoint:{v[0]}", v[1]))
    # 5 tokenized path verb (trailing segment)
    v = _trailing_verb(path_tokens)
    if v:
        evidence.append((5, f"path_token:{v[0]}", v[1]))

    # ── WS5: conflict detection among the STRONGEST available level ──────────
    if evidence:
        best_level = min(e[0] for e in evidence)
        strongest = [e for e in evidence if e[0] == best_level]
        actions = {e[2] for e in strongest}
        if len(actions) > 1:
            return {"action": MANUAL, "source": "conflict",
                    "confidence": "CONFLICT", "tokens": path_tokens,
                    "rejected": "|".join(f"{e[1]}={e[2]}" for e in strongest),
                    "conflict": f"level {best_level} sources disagree: {sorted(actions)}"}
        chosen = strongest[0]
        rejected = "|".join(f"{e[1]}={e[2]}" for e in evidence if e[2] != chosen[2])
        return {"action": chosen[2], "source": chosen[1],
                "confidence": "TOKEN", "tokens": path_tokens,
                "rejected": rejected, "conflict": ""}

    # 6 strong HTTP fallback
    if method == "DELETE":
        return {"action": "delete", "source": "http_delete", "confidence": "HTTP_STRONG",
                "tokens": path_tokens, "rejected": "", "conflict": ""}
    if method in ("PUT", "PATCH") and has_proven_write:
        return {"action": "update", "source": "http_put_with_write",
                "confidence": "HTTP_STRONG", "tokens": path_tokens,
                "rejected": "", "conflict": ""}

    # 7 no reliable evidence -- POST never defaults to create
    return {"action": MANUAL, "source": "no_action_evidence",
            "confidence": "NONE", "tokens": path_tokens, "rejected": "",
            "conflict": "POST/other with no action token and no strong HTTP signal"}


def inventory():
    """WS1 — every synonym rule, described."""
    rows = []
    for verb, action in sorted(VERB_TO_ACTION.items()):
        rows.append({"rule_id": f"V_{verb}", "verb_token": verb, "action": action,
                     "input_source": "tokenized path/endpoint/service",
                     "separator_dependent": "no -- token-based",
                     "http_method_inference": "no", "confidence": "TOKEN"})
    return rows


if __name__ == "__main__":
    cases = [
        ("POST", "/v1/tenants/{tenant_id}/engines/bulk-disable", "bulk_disable", ("bulk_disable_engines",)),
        ("POST", "/v1/tenants/{tenant_id}/engines/bulk-enable", "bulk_enable", ("bulk_enable_engines",)),
        ("POST", "/v1/tenants/{tenant_id}/terminate/confirm", "confirm_termination", ("confirm_termination",)),
        ("POST", "/v1/security/api-keys/{id}/rotate", "rotate_key", ("rotate_api_key",)),
        ("POST", "/v1/chat/conversations", "create_conversation", ("get_or_create_conversation",)),
        ("POST", "/v1/appointments/{id}/confirm", "confirm_hold", ("confirm_hold",)),
        ("POST", "/v1/commerce/.../badges/recalculate", "recalculate_badges", ("recalculate_badges",)),
        ("DELETE", "/v1/media/{media_id}", "delete_media", ("delete_asset",)),
        ("POST", "/v1/some/unknown/thing", "do_thing", ()),
    ]
    for method, path, fn, svc in cases:
        r = infer_action(method=method, path=path, endpoint_name=fn, service_methods=svc)
        print(f"  {method:6} {path[:46]:46} -> {r['action']:12} ({r['source']})")
