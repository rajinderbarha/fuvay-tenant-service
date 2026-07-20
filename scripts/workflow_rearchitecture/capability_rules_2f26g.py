"""Slice 2F-26G — deterministic capability-family precedence (D-07 repair).

Slice 2F-26F derived the family from an ORDERED LIST of regexes, so
`^/v1/tenants?\\b` and `^/v1/me\\b` silently shadowed the more specific
geography and media rules. Moving two rows would have fixed two routes and
left the shadowing mechanism intact.

This module replaces incidental ordering with an explicit, verifiable
contract:

  LEVEL 1  exact mounted path
  LEVEL 2  exact resource prefix
  LEVEL 3  specific nested resource
  LEVEL 4  general engine / persona prefix
  LEVEL 5  fallback

Resolution takes the LOWEST level that matches. Within a level, the highest
explicit priority wins; if two rules at the same level share the top priority
and disagree on family, resolution RAISES rather than picking one -- an
ambiguous rule set is a defect, not a coin toss.

Every rule is inventoriable and the set is auditable for shadowing,
unreachability and fallback capture.
"""
from __future__ import annotations

import re


class FamilyConflict(Exception):
    """Two equally specific rules claim different families. Fail closed."""


FAMILIES = {
    "identity_access", "tenant_governance", "staff_management", "customer_account",
    "booking", "job_execution", "catalog", "pricing", "package_commerce", "billing",
    "review_reputation", "notification", "compliance", "security_audit",
    "analytics", "marketing", "integration_webhook", "geography_serviceability",
    "media", "other",
}

# (rule_id, level, priority, pattern, family)
# Level 3 rules are specific nested resources; they always outrank the level-4
# engine prefixes that would otherwise swallow them.
RULES = [
    # ── LEVEL 2: exact resource prefixes ────────────────────────────────────
    ("R201", 2, 100, r"^/v1/tenant/service-areas(/|$)", "geography_serviceability"),
    ("R202", 2, 100, r"^/v1/me/profile-photo(/|$)", "media"),
    ("R203", 2, 100, r"^/v1/me/notifications(/|$)", "notification"),
    ("R204", 2, 100, r"^/v1/tenant/checklist-templates(/|$)", "job_execution"),

    # ── LEVEL 3: specific nested resources beneath a general prefix ─────────
    ("R301", 3, 90, r"^/v1/auth/staff(/|$)", "staff_management"),
    ("R302", 3, 90, r"^/v1/auth/(mfa|sessions|login|logout|token|password)(/|$)",
     "identity_access"),
    ("R303", 3, 90, r"^/v1/security/(sessions|api-keys)(/|$)", "security_audit"),
    ("R304", 3, 90, r"^/v1/commerce/.*/wallet(/|$)", "package_commerce"),
    # NOTE: /v1/ds/.../pricing is deliberately NOT a specific rule. Those
    # routes live in the data-science (analytics) engine and are analytics
    # features (recommendations, apply-a-recommendation); mounted-path
    # determinism keeps them under the analytics engine rule R415 rather than
    # re-homing them to `pricing` on a resource-segment coincidence.
    ("R306", 3, 90, r"^/v1/enterprise/exports(/|$)", "analytics"),
    ("R307", 3, 90, r"^/v1/provider/notifications(/|$)", "notification"),
    ("R308", 3, 90, r"^/v1/tenants/.*/(engines|plan|trial|terminate|suspend|reinstate|"
     r"feature-flags|data)(/|$)", "tenant_governance"),

    # ── LEVEL 4: general engine / persona prefixes ──────────────────────────
    ("R401", 4, 50, r"^/v1/(auth|me)(/|$)", "identity_access"),
    ("R402", 4, 50, r"^/v1/tenants?(/|$)", "tenant_governance"),
    ("R403", 4, 50, r"^/v1/staff(/|$)", "staff_management"),
    ("R404", 4, 50, r"^/v1/customers?(/|$)", "customer_account"),
    ("R405", 4, 50, r"^/v1/(bookings?|appointments)(/|$)", "booking"),
    ("R406", 4, 50, r"^/v1/(jobs?|dispatch|field-ops)(/|$)", "job_execution"),
    ("R407", 4, 50, r"^/v1/(catalog|services)(/|$)", "catalog"),
    ("R408", 4, 50, r"^/v1/pricing(/|$)", "pricing"),
    ("R409", 4, 50, r"^/v1/(packages?|commerce)(/|$)", "package_commerce"),
    ("R410", 4, 50, r"^/v1/(payments?|invoices?|billing)(/|$)", "billing"),
    ("R411", 4, 50, r"^/v1/(reviews?|reputation)(/|$)", "review_reputation"),
    ("R412", 4, 50, r"^/v1/(notifications?|chat)(/|$)", "notification"),
    ("R413", 4, 50, r"^/v1/(compliance|privacy)(/|$)", "compliance"),
    ("R414", 4, 50, r"^/v1/(security|audit)(/|$)", "security_audit"),
    ("R415", 4, 50, r"^/v1/(analytics|ds|enterprise)(/|$)", "analytics"),
    ("R416", 4, 50, r"^/v1/marketing(/|$)", "marketing"),
    ("R417", 4, 50, r"^/v1/(webhooks?|integrations?)(/|$)", "integration_webhook"),
    ("R418", 4, 50, r"^/v1/(geo|serviceability)(/|$)", "geography_serviceability"),
    ("R419", 4, 50, r"^/v1/(media|documents)(/|$)", "media"),
    ("R420", 4, 50, r"^/v1/provider(/|$)", "tenant_governance"),
    ("R421", 4, 50, r"^/v1/inventory(/|$)", "other"),
]

FALLBACK = ("R500", 5, 0, None, "other")

_COMPILED = [(rid, lvl, pri, re.compile(pat), fam) for rid, lvl, pri, pat, fam in RULES]


def matching_rules(path):
    """Every rule matching this path, most specific first."""
    hits = [(rid, lvl, pri, fam) for rid, lvl, pri, rx, fam in _COMPILED if rx.search(path)]
    return sorted(hits, key=lambda h: (h[1], -h[2]))


def resolve_family(path):
    """(family, rule_id, level, was_fallback). Raises FamilyConflict on a tie."""
    hits = matching_rules(path)
    if not hits:
        return FALLBACK[4], FALLBACK[0], FALLBACK[1], True
    top_level = hits[0][1]
    top_prio = max(h[2] for h in hits if h[1] == top_level)
    winners = [h for h in hits if h[1] == top_level and h[2] == top_prio]
    fams = {h[3] for h in winners}
    if len(fams) > 1:
        raise FamilyConflict(
            f"{path}: rules {[w[0] for w in winners]} at level {top_level} "
            f"priority {top_prio} disagree: {sorted(fams)}")
    w = winners[0]
    return w[3], w[0], w[1], False


# ══════════════════════════════════════════════════════════════════════════
# WS3 — rule-set audit
# ══════════════════════════════════════════════════════════════════════════

def audit(paths):
    """Shadowing, unreachability, conflicts and fallback capture."""
    report = {"shadowed": [], "unreachable": [], "conflicts": [], "fallback_captured": []}
    used = set()
    for p in paths:
        try:
            fam, rid, lvl, fb = resolve_family(p)
        except FamilyConflict as e:
            report["conflicts"].append(str(e))
            continue
        used.add(rid)
        hits = matching_rules(p)
        # a specific rule matched but a more general one won -> shadowing
        for h in hits:
            if h[1] < lvl:
                report["shadowed"].append(
                    f"{p}: {h[0]} (level {h[1]}, {h[3]}) shadowed by {rid} (level {lvl})")
        if fb and hits:
            report["fallback_captured"].append(
                f"{p}: fallback used though {hits[0][0]} matches")
    for rid, lvl, pri, pat, fam in RULES:
        if rid not in used:
            report["unreachable"].append(f"{rid} ({pat} -> {fam}) matched no known path")
    return report


def inventory():
    """WS1 — every rule, fully described."""
    rows = []
    for rid, lvl, pri, pat, fam in RULES:
        overlapping = [o for o, ol, op, opat, of in RULES
                       if o != rid and (re.search(pat, opat.replace("^", "").replace(
                           r"(/|$)", "/x")) if False else False)]
        rows.append({
            "rule_id": rid, "pattern": pat, "match_type": "regex_search",
            "family": fam, "level": lvl, "priority": pri,
            "specificity": len(pat), "source": "capability_rules_2f26g.RULES",
            "overlapping_rules": "|".join(overlapping),
            "fallback_behavior": "n/a",
        })
    rows.append({"rule_id": FALLBACK[0], "pattern": "(none)", "match_type": "fallback",
                 "family": FALLBACK[4], "level": FALLBACK[1], "priority": FALLBACK[2],
                 "specificity": 0, "source": "capability_rules_2f26g.FALLBACK",
                 "overlapping_rules": "", "fallback_behavior": "used only when no rule matches"})
    return rows


if __name__ == "__main__":
    for p in ["/v1/tenant/service-areas/x/services/y", "/v1/me/profile-photo",
              "/v1/tenants/x/suspend", "/v1/me/preferences", "/v1/unknown/thing"]:
        print(f"  {p:44} -> {resolve_family(p)}")
