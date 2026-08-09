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

# How a banner is drawn. The app ships one renderer per style, so this is a
# fixed vocabulary rather than free text -- a style the app cannot draw would
# leave admin with a saved campaign that renders as nothing.
STYLE_HERO = "hero"          # large artwork card in the top carousel
STYLE_FESTIVAL = "festival"  # full-bleed accent colour + badge, for seasonal runs
STYLE_STRIP = "strip"        # one-line strip: icon, short copy, inline CTA
CAMPAIGN_STYLES = (STYLE_HERO, STYLE_FESTIVAL, STYLE_STRIP)

# Where on Home it appears. Same reasoning: each slot is a real position the app
# renders, and the section settings below can disable any of them.
PLACEMENT_TOP = "campaign_top"
PLACEMENT_MID = "campaign_mid"
PLACEMENT_BOTTOM = "campaign_bottom"
CAMPAIGN_PLACEMENTS = (PLACEMENT_TOP, PLACEMENT_MID, PLACEMENT_BOTTOM)

ERR_INVALID_STYLE = "CAMPAIGN_INVALID_DISPLAY_STYLE"
ERR_INVALID_PLACEMENT = "CAMPAIGN_INVALID_PLACEMENT"

ERR_CAMPAIGN_NOT_FOUND = "CAMPAIGN_NOT_FOUND"
ERR_INVALID_DEEPLINK = "CAMPAIGN_INVALID_DEEPLINK"
ERR_INVALID_DATE_WINDOW = "CAMPAIGN_INVALID_DATE_WINDOW"

MAX_ACTIVE_CAMPAIGNS_RETURNED = 10
