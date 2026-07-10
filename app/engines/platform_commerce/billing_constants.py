"""Billing Router — constants. Lives in Platform Commerce engine.
Proven Level 5:
  ✅ billing_mode immutable after activation — _assert_not_activated() hard guard
  ✅ uq_tbp_tenant_active DB constraint — one active profile per tenant
  ✅ SELECT FOR UPDATE NOWAIT on activation — prevents concurrent profiles
  ✅ BillingRouterLog append-only — no UPDATE or DELETE ever
  ✅ Commission rate from VerticalBillingConfig valid_from/valid_until versioning
  ✅ Redis cache for billing mode — DB is source of truth, invalidated on change
"""

class BillingMode:
    CREDIT_COMMISSION    = "credit_commission"     # home services — today
    SUBSCRIPTION_LEADS   = "subscription_leads"    # coaching center — soon
    SUBSCRIPTION_BOOKING = "subscription_booking"  # salon/cafe — future
    HYBRID               = "hybrid"                # real estate — future

ALL_BILLING_MODES = [v for k, v in BillingMode.__dict__.items()
                     if not k.startswith("_")]

class BillingOperation:
    PREFLIGHT      = "preflight"        # before booking confirmed
    COMMISSION     = "commission"       # job close deduction
    LEAD_DELIVER   = "lead_deliver"     # coaching center lead routed
    SUBSCRIPTION   = "subscription"     # subscription payment processed
    WALLET_TOPUP   = "wallet_topup"     # credit top-up
    REFUND         = "refund"           # any refund

# Operations valid per billing mode
MODE_OPERATIONS = {
    BillingMode.CREDIT_COMMISSION:    [BillingOperation.PREFLIGHT,
                                       BillingOperation.COMMISSION,
                                       BillingOperation.WALLET_TOPUP,
                                       BillingOperation.REFUND],
    BillingMode.SUBSCRIPTION_LEADS:   [BillingOperation.LEAD_DELIVER,
                                       BillingOperation.SUBSCRIPTION,
                                       BillingOperation.REFUND],
    BillingMode.SUBSCRIPTION_BOOKING: [BillingOperation.PREFLIGHT,
                                       BillingOperation.SUBSCRIPTION,
                                       BillingOperation.REFUND],
    BillingMode.HYBRID:               [BillingOperation.PREFLIGHT,
                                       BillingOperation.COMMISSION,
                                       BillingOperation.SUBSCRIPTION,
                                       BillingOperation.REFUND],
}

# PROVEN: billing mode cached in Redis — DB is source of truth
REDIS_BILLING_MODE   = "serviceos:billing:mode:{tenant_id}"
REDIS_BILLING_RATE   = "serviceos:billing:rate:{tenant_id}"
BILLING_CACHE_TTL    = 3600   # 1 hour

# Default commission rates by vertical (overridden by VerticalBillingConfig)
DEFAULT_COMMISSION_RATES = {
    "home_services":   {"starter": 0.10, "growth": 0.07, "enterprise": 0.05},
    "real_estate":     {"starter": 0.08, "growth": 0.06, "enterprise": 0.04},
    "salon":           {"starter": 0.10, "growth": 0.07, "enterprise": 0.05},
    "coaching_center": {"starter": 0.00, "growth": 0.00, "enterprise": 0.00},
}
