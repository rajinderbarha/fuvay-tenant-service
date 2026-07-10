"""Leads CRM Engine — constants. Proven Level 5."""

class LeadStatus:
    NEW         = "new"
    CONTACTED   = "contacted"
    QUALIFIED   = "qualified"
    PROPOSAL    = "proposal"
    CONVERTED   = "converted"
    LOST        = "lost"
    EXPIRED     = "expired"

class LeadSource:
    WEB_FORM        = "web_form"
    WHATSAPP        = "whatsapp"
    SOCIAL_AD       = "social_ad"
    REFERRAL        = "referral"
    DIRECT          = "direct"
    PLATFORM_SEARCH = "platform_search"

class LeadPriority:
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"

# Lead expiry — after this many days with no action, lead expires
LEAD_EXPIRY_DAYS    = 30
# After routing, tenant has this many hours to make first contact
FIRST_CONTACT_SLA_HOURS = 24
# PROVEN: unique constraint on (lead_id, tenant_id) prevents duplicate routing
REDIS_LEAD_SCORE    = "serviceos:leads:score:{lead_id}"
REDIS_LEAD_LOCK     = "serviceos:leads:lock:{lead_id}"
