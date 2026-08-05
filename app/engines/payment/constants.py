"""Payment Engine — constants. Proven Level 5."""
class PaymentStatus:
    PENDING    = "pending"
    PROCESSING = "processing"
    CAPTURED   = "captured"
    FAILED     = "failed"
    REFUNDED   = "refunded"
    PARTIAL_REFUND = "partial_refund"

class PaymentGateway:
    RAZORPAY = "razorpay"
    STRIPE   = "stripe"

class PaymentType:
    CUSTOMER_PAYMENT = "customer_payment"
    SUBSCRIPTION     = "subscription"
    PAYOUT           = "payout"
    REFUND           = "refund"
    # Customer-paid platform fee (vertical_monetization). Referenced by
    # charge_service but never declared here, so that engine could not
    # create a payment order at all. This money belongs 100% to the
    # platform -- see process_payment_webhook, which must never settle any
    # part of it to a tenant.
    CUSTOMER_PLATFORM_FEE = "customer_platform_fee"

class PayoutStatus:
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"

# Dunning schedule — days after first failure
DUNNING_RETRY_DAYS = [3, 7, 14]
MAX_DUNNING_ATTEMPTS = 3

# Invoice number Redis key — INCR ensures atomic sequential numbers
REDIS_INVOICE_COUNTER = "serviceos:payment:invoice_counter:{tenant_id}"
REDIS_PAYMENT_IDEM    = "serviceos:payment:idem:{payment_id}"

PLATFORM_FEE_PCT      = 0.02  # 2% platform fee on customer payments
TAX_PCT               = 0.18  # 18% GST
