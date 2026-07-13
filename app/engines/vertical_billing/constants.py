"""Vertical Billing — orphaned scaffold, NOT the canonical implementation.

MODULE-L5-00A finding: this directory has no router, no model, and no
active caller anywhere in the codebase. The real, working
VerticalBillingConfig / BillingRouter implementation this file's constants
describe lives entirely in `app.engines.platform_commerce`
(billing_constants.py, billing_models.py, billing_router.py) — see
docs/module-l5/00a-vertical-billing-disposition.md for the full
investigation. This module is scheduled for deletion (backlog item BL-002);
do not treat it as canonical or import from it.
"""

class Vertical:
    HOME_SERVICES   = "home_services"
    COACHING_CENTER = "coaching_center"
    REAL_ESTATE     = "real_estate"
    SALON           = "salon"
    CAFE            = "cafe"

class BillingMode:
    CREDIT_COMMISSION   = "credit_commission"    # Home services: pay upfront, deduct commission
    SUBSCRIPTION_LEAD   = "subscription_lead"    # Coaching: monthly fee, lead access
    SUBSCRIPTION_FLAT   = "subscription_flat"    # Future: monthly fee, flat access
    HYBRID              = "hybrid"               # Future: credits + subscription

class LeadRoutingMode:
    NONE            = "none"           # Home services — no lead routing
    SUBSCRIPTION    = "subscription"   # Coaching — leads by plan tier
    PAY_PER_LEAD    = "pay_per_lead"   # Future — per-lead credit charge

# ── Commission rates by plan per vertical ──────────────────────────────────
# Home services only — coaching center has no commission
COMMISSION_RATES = {
    ("home_services", "no_plan"):   0.10,
    ("home_services", "starter"):   0.10,
    ("home_services", "growth"):    0.07,
    ("home_services", "enterprise"):0.05,
}

# ── Lead caps per plan per vertical ───────────────────────────────────────
# Coaching center only — home services has no lead cap
LEAD_CAPS_MONTHLY = {
    ("coaching_center", "basic"):   50,
    ("coaching_center", "growth"):  200,
    ("coaching_center", "premium"): 999999,  # unlimited
}

# ── Subscription pricing per vertical per plan ─────────────────────────────
SUBSCRIPTION_PRICES = {
    ("coaching_center", "basic",   "monthly"): 99900,   # INR 999
    ("coaching_center", "growth",  "monthly"): 249900,  # INR 2499
    ("coaching_center", "premium", "monthly"): 499900,  # INR 4999
    ("home_services",  "starter",  "monthly"): 0,       # free — revenue via commission
    ("home_services",  "growth",   "monthly"): 0,       # commission rate drops instead
    ("home_services",  "enterprise","monthly"): 0,      # negotiated
}

REDIS_BILLING_CONFIG   = "serviceos:vb:config:{tenant_id}"
REDIS_LEAD_COUNTER     = "serviceos:vb:leads:{tenant_id}:{period_id}"
REDIS_VERTICAL_CACHE   = "serviceos:vb:vertical:{tenant_id}"
