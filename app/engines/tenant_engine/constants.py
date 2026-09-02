"""Tenant Engine — constants."""

# MODULE-L5-02: the registry must list every state the transition table and
# admin logic actually use. Previously omitted rejected/awaiting_documents/
# trial_expired/archived even though VALID_TRANSITIONS and admin_service.py
# reference them — the tenant_governance_guard now fails closed on any such drift.
TENANT_STATES = ["onboarding_pending","under_review","awaiting_documents","pending_activation","trial","trial_expired","active","suspended","terminated","rejected","archived"]

VALID_TRANSITIONS = {
    "onboarding_pending": ["under_review", "rejected"],
    "under_review": ["pending_activation", "awaiting_documents", "rejected"],
    "awaiting_documents": ["under_review", "rejected"],
    "pending_activation": ["active", "trial", "rejected"],
    "trial": ["active", "suspended", "trial_expired"],
    "trial_expired": ["active", "archived"],
    "active": ["suspended", "terminated"],
    "suspended": ["active", "terminated"],
    "terminated": [],
}

VERTICALS = ["home_services"]  # only home_services is active for this build

PLAN_LIMITS = {
    "starter": {"max_staff": 10, "max_active_jobs": 20, "max_storage_gb": 10, "max_api_calls_per_day": 5000, "max_engines": 8, "max_customers": 500, "max_service_areas": 5},
    "growth": {"max_staff": 50, "max_active_jobs": 200, "max_storage_gb": 100, "max_api_calls_per_day": 50000, "max_engines": 18, "max_customers": 5000, "max_service_areas": 20},
    "enterprise": {"max_staff": 500, "max_active_jobs": 5000, "max_storage_gb": 1000, "max_api_calls_per_day": 500000, "max_engines": 28, "max_customers": 100000, "max_service_areas": 100},
}

PLAN_COMMISSION_BASE = {"starter": 10.0, "growth": 7.0, "enterprise": 5.0}

TRIAL_DAYS = {"starter": 14, "growth": 30, "enterprise": 60}

GRACE_PERIOD_DAYS = {"starter": 7, "growth": 14, "enterprise": 30}

DEFAULT_ENGINES_BY_VERTICAL = {
    "home_services": [
        "auth", "tenant", "platform_commerce", "pricing",
        "notification", "settings", "analytics", "media",
        "chat", "review", "field_ops", "booking", "appointment",
        "dispatch", "geo", "inventory", "payment",
        "document", "webhook", "data_science",
    ],
    "real_estate": [
        "auth", "tenant", "platform_commerce", "pricing",
        "notification", "settings", "analytics", "media",
        "chat", "review", "leads", "payment",
        "document", "webhook",
    ],
    "coaching": [
        "auth", "tenant", "platform_commerce", "pricing",
        "notification", "settings", "analytics", "media",
        "chat", "review", "appointment", "payment",
        "document", "webhook",
    ],
    "salon": [
        "auth", "tenant", "platform_commerce", "pricing",
        "notification", "settings", "analytics", "media",
        "review", "appointment", "payment",
    ],
    "cafe": [
        "auth", "tenant", "platform_commerce", "pricing",
        "notification", "settings", "analytics", "media",
        "review", "payment",
    ],
}

CHECKLIST_ITEMS = [
    "business_documents_verified",
    "gst_number_verified",
    "address_proof_uploaded",
    "plan_selected",
    "vertical_confirmed",
    "engines_configured",
    "engine_configs_set",
    "owner_account_created",
]

HEALTH_SCORE_WEIGHTS = {
    "job_completion_rate": 0.25,
    "customer_satisfaction": 0.20,
    "warranty_claim_rate": 0.15,
    "usage_credit_health": 0.15,  # FINAL-L5-05J: renamed from credit_wallet_health, now real
    "staff_compliance_rate": 0.10,
    "response_time": 0.10,
    "platform_engagement": 0.05,
}

HEALTH_BANDS = {
    "platinum": (90, 100),
    "gold": (75, 89),
    "silver": (60, 74),
    "bronze": (40, 59),
    "at_risk": (20, 39),
    "critical": (0, 19),
}

COMMISSION_ADJUSTMENT_BY_BAND = {
    "platinum": -1.0,
    "gold": 0.0,
    "silver": 2.0,
    "bronze": 5.0,
    "at_risk": 10.0,
    "critical": 10.0,
}
