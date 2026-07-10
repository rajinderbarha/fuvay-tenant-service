"""Review Engine — constants. Proven Level 5.
Signal weights verified sum == 1.0 in test suite.
"""
# ── Review signal weights ────────────────────────────────────────────────────
# PROVEN: assert abs(sum(REVIEW_SIGNAL_WEIGHTS.values()) - 1.0) < 0.001
REVIEW_SIGNAL_WEIGHTS = {
    "overall_quality": 0.35,
    "punctuality":     0.20,
    "cleanliness":     0.15,
    "value_for_money": 0.20,
    "communication":   0.10,
}

class ReviewStatus:
    PENDING   = "pending"
    PUBLISHED = "published"
    FLAGGED   = "flagged"
    REMOVED   = "removed"

class ReviewRequestStatus:
    SENT      = "sent"
    SUBMITTED = "submitted"
    EXPIRED   = "expired"
    MISSED    = "missed"

REVIEW_REQUEST_EXPIRY_DAYS = 7
REVIEW_MIN_SCORE           = 1
REVIEW_MAX_SCORE           = 5
REVIEW_REQUEST_DELAY_MINUTES = 30   # Celery countdown after job.closed

# Health signals published on review submission
REVIEW_HEALTH_SIGNAL = "avg_review_score"
REPLY_RATE_SIGNAL    = "review_reply_rate"

# Aggregate recomputed every 6 hours via Celery beat
AGGREGATE_TTL_HOURS  = 6
REDIS_REVIEW_AGG     = "serviceos:review:agg:{entity_type}:{entity_id}"
