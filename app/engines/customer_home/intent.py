"""What a customer is actually trying to do: repair something, or get advice.

The problem list mixes two different intents. "AC Not Cooling" is a fault -- the
customer knows what is wrong and wants it fixed. "New AC Installation" or a site
visit is not a fault at all; it is a job to be scoped, quoted and advised on. They
deserve different sections, because a customer arrives on Home in one mode or the
other and scanning a single mixed list makes them read past most of it.

Classification is by KEYWORD against the admin-authored name, and it is a
heuristic -- stated as one, and kept in this single module so the vocabulary is
reviewable in one place. Anything that matches neither is left UNCLASSIFIED and
appears in neither section: putting it in the wrong one is worse than leaving it to
the general problem grids, which show everything.
"""
from __future__ import annotations

import re

INTENT_REPAIR = "repair"
INTENT_CONSULT = "consult"
INTENT_NONE = None

# A fault: something already broken, leaking, tripping or not working.
_REPAIR_PATTERNS = (
    r"not\s+(cooling|starting|working|draining|spinning)",
    r"\bnot\s+work", r"\bno\s+power\b", r"\bfault", r"\bbroken\b", r"\bbreak",
    r"leak", r"blockage", r"blocked", r"\btrip\b", r"\bmcb\b", r"short\s*circuit",
    r"sparking", r"\bnoise\b", r"noisy", r"\bsmell\b", r"\bodor\b", r"\bodour\b",
    r"low\s+(cooling|water|pressure)", r"overflow", r"\bissue\b", r"\brepair\b",
    r"refill", r"stain", r"infestation", r"\bpest\b",
)

# Advice, scoping or a quote -- work that has to be understood before it is priced.
_CONSULT_PATTERNS = (
    r"\binquiry\b", r"\benquiry\b", r"\bconsult", r"\badvice\b", r"\bquote\b",
    r"\bestimate\b", r"site\s*visit", r"\bsurvey\b", r"\bdemo\b", r"\bnew\s+install",
    r"\binstallation\b", r"\binstall\b", r"\bsetup\b", r"\bshifting\b",
    r"\brelocat", r"\bplanning\b", r"\bdesign\b", r"needed$", r"required$",
)


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify_intent(name: str | None) -> str | None:
    """"repair", "consult", or None when the wording says neither.

    REPAIR is tested first: "Low Cooling / Gas Refill Needed" ends in "Needed",
    which the consult list would otherwise claim, but a gas refill is plainly a
    fix. When both could match, the fault wins -- it is the more specific reading.
    """
    text = (name or "").strip().lower()
    if not text:
        return INTENT_NONE
    if _matches(_REPAIR_PATTERNS, text):
        return INTENT_REPAIR
    if _matches(_CONSULT_PATTERNS, text):
        return INTENT_CONSULT
    return INTENT_NONE
