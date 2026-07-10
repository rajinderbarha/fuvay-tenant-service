"""Dispatch Engine — constants."""

class DispatchMode:
    MANUAL      = "manual"
    AUTO_ASSIGN = "auto_assign"
    BROADCAST   = "broadcast"

class DispatchStatus:
    PENDING   = "pending"
    ASSIGNED  = "assigned"
    ACCEPTED  = "accepted"
    REJECTED  = "rejected"
    ESCALATED = "escalated"
    EXPIRED   = "expired"

# Default scoring weights (tenant-configurable via Settings engine)
DEFAULT_SCORE_WEIGHTS = {
    "distance":         0.40,
    "performance":      0.35,
    "active_job_count": 0.15,
    "specialisation":   0.10,
}

BROADCAST_ACCEPT_TTL_MINUTES = 15
AUTO_ASSIGN_ACCEPT_SLA_MINUTES = 10
MAX_ESCALATION_ATTEMPTS = 3

REDIS_BROADCAST   = "serviceos:dispatch:broadcast:{job_id}"
REDIS_DISPATCH_LOCK = "serviceos:dispatch:lock:{job_id}"
