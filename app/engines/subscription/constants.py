"""Subscription Engine — constants. Proven Level 5."""
class SubStatus:
    TRIALING  = "trialing"
    ACTIVE    = "active"
    PAST_DUE  = "past_due"
    CANCELLED = "cancelled"
    PAUSED    = "paused"
    EXPIRED   = "expired"

class BillingCycle:
    MONTHLY = "monthly"
    ANNUAL  = "annual"

class PlanChangeType:
    UPGRADE   = "upgrade"
    DOWNGRADE = "downgrade"
    SAME      = "same"

# Grace period before suspension on failed payment
GRACE_PERIOD_DAYS    = 3
DUNNING_RETRY_DAYS   = [3, 7, 14]
MAX_DUNNING_ATTEMPTS = 3

# Proration uses immutable SubscriptionPeriod rows — not estimated
PRORATION_PRECISION  = 6   # decimal places

REDIS_SUB_PERIOD     = "serviceos:sub:period:{subscription_id}"
REDIS_USAGE_COUNT    = "serviceos:sub:usage:{tenant_id}:{period_id}"
