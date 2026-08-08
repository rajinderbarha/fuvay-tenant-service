"""Masked calling — controlled vocabularies.

Backend is the sole authority: no frontend flag may declare a call connected,
change a direction, or bypass the not-configured state.
"""

# ── Session status ────────────────────────────────────────────────────────
STATUS_REQUESTED = "requested"      # we asked the provider to bridge
STATUS_RINGING = "ringing"
STATUS_CONNECTED = "connected"      # both legs joined -- a real conversation
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_NO_ANSWER = "no_answer"
STATUS_BUSY = "busy"
STATUS_EXPIRED = "expired"          # binding outlived its job/window
SESSION_STATUSES = {
    STATUS_REQUESTED, STATUS_RINGING, STATUS_CONNECTED, STATUS_COMPLETED,
    STATUS_FAILED, STATUS_NO_ANSWER, STATUS_BUSY, STATUS_EXPIRED,
}
# Statuses that prove a conversation actually happened. Only these satisfy the
# "call the customer first" task -- a ring-out must not tick it off.
CONNECTED_STATUSES = {STATUS_CONNECTED, STATUS_COMPLETED}
TERMINAL_STATUSES = {
    STATUS_COMPLETED, STATUS_FAILED, STATUS_NO_ANSWER, STATUS_BUSY, STATUS_EXPIRED,
}

# ── Direction ─────────────────────────────────────────────────────────────
DIR_STAFF_TO_CUSTOMER = "staff_to_customer"
DIR_CUSTOMER_TO_STAFF = "customer_to_staff"
DIRECTIONS = {DIR_STAFF_TO_CUSTOMER, DIR_CUSTOMER_TO_STAFF}

# ── Initiator ─────────────────────────────────────────────────────────────
ROLE_STAFF = "staff"
ROLE_CUSTOMER = "customer"
INITIATOR_ROLES = {ROLE_STAFF, ROLE_CUSTOMER}

# How long a call binding stays valid. Short on purpose: the binding exists for
# one conversation about one job, not as a standing line between two people.
BINDING_TTL_MINUTES = 30

# ── Error codes ───────────────────────────────────────────────────────────
ERR_CALLING_NOT_CONFIGURED = "MASKED_CALLING_NOT_CONFIGURED"
ERR_JOB_NOT_FOUND = "MASKED_CALLING_JOB_NOT_FOUND"
ERR_JOB_NOT_CALLABLE = "MASKED_CALLING_JOB_NOT_CALLABLE"
ERR_NO_CUSTOMER_NUMBER = "MASKED_CALLING_NO_CUSTOMER_NUMBER"
ERR_NO_STAFF_NUMBER = "MASKED_CALLING_NO_STAFF_NUMBER"
ERR_PROVIDER_FAILED = "MASKED_CALLING_PROVIDER_FAILED"
ERR_WEBHOOK_UNAUTHORIZED = "MASKED_CALLING_WEBHOOK_UNAUTHORIZED"

# A job in a terminal state has no legitimate reason for a fresh call binding.
NON_CALLABLE_JOB_STATUSES = {
    "completed", "cancelled", "failed", "closed_estimate_declined",
}
