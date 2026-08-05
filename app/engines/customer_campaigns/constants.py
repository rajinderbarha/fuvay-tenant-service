"""Customer campaign/banner constants."""

# Deep-link targets are restricted to known, safe in-app destinations —
# never an arbitrary/external URL (Phase 11 requirement: "Validate deep
# links against an allowlist. Do not accept arbitrary executable URLs.").
ALLOWED_DEEPLINK_PREFIXES = (
    "app://home",
    "app://category/",
    "app://service/",
    "app://booking/",
    "app://offers",
)

ERR_CAMPAIGN_NOT_FOUND = "CAMPAIGN_NOT_FOUND"
ERR_INVALID_DEEPLINK = "CAMPAIGN_INVALID_DEEPLINK"
ERR_INVALID_DATE_WINDOW = "CAMPAIGN_INVALID_DATE_WINDOW"

MAX_ACTIVE_CAMPAIGNS_RETURNED = 10
