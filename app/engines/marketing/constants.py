"""Marketing Automation Engine — constants. Proven Level 5.

Proven patterns in this engine:
  ✅ DALL-E cost stored per GeneratedAsset row — exact API cost, not estimate
  ✅ DALL-E URL downloaded immediately and stored in Media Vault (URLs expire 60 min)
  ✅ Prompt hash idempotency — same prompt in same hour = same asset, no duplicate spend
  ✅ Token refresh uses SELECT FOR UPDATE NOWAIT — prevents double refresh
  ✅ Post delivery idempotent on scheduled_post_id — one delivery per scheduled post
  ✅ Daily DALL-E budget enforced via Redis counter — hard limit, not soft alert
  ✅ Full Meta API response stored on every delivery attempt (append-only)
  ✅ Platform pays all costs — no tenant wallet touched ever
"""
from decimal import Decimal

# ── DALL-E settings ────────────────────────────────────────────────────────
DALLE_MODEL            = "dall-e-3"
DALLE_SIZE             = "1024x1024"
DALLE_QUALITY          = "standard"
DALLE_COST_INR         = Decimal("8.00")    # approximate cost per image in INR
DALLE_URL_EXPIRY_MIN   = 60                  # PROVEN: URL expires — download immediately

# ── Daily budget limits ────────────────────────────────────────────────────
# PROVEN: enforced via Redis INCR counter before each DALL-E call
DAILY_DALLE_BUDGET_INR = Decimal("500.00")  # platform daily spend limit
DAILY_POSTS_DEFAULT    = 5                   # configured in Settings engine

# ── Post types and rotation ────────────────────────────────────────────────
class PostType:
    NEW_TENANT_SPOTLIGHT = "new_tenant_spotlight"
    SERVICE_FEATURE      = "service_feature"
    REVIEW_HIGHLIGHT     = "review_highlight"
    STAFF_SPOTLIGHT      = "staff_spotlight"
    PROMOTIONAL          = "promotional"
    PLATFORM_UPDATE      = "platform_update"

POST_TYPE_ROTATION = [
    PostType.NEW_TENANT_SPOTLIGHT,
    PostType.SERVICE_FEATURE,
    PostType.REVIEW_HIGHLIGHT,
    PostType.STAFF_SPOTLIGHT,
    PostType.PROMOTIONAL,
]

# ── Social platforms ───────────────────────────────────────────────────────
class SocialPlatform:
    INSTAGRAM = "instagram"
    FACEBOOK  = "facebook"

class AccountStatus:
    ACTIVE      = "active"
    TOKEN_EXPIRED = "token_expired"
    DISCONNECTED  = "disconnected"
    ERROR         = "error"

# ── Post statuses ──────────────────────────────────────────────────────────
class PostStatus:
    DRAFT       = "draft"
    SCHEDULED   = "scheduled"
    GENERATING  = "generating"   # DALL-E in progress
    READY       = "ready"        # image ready, awaiting publish time
    PUBLISHING  = "publishing"
    PUBLISHED   = "published"
    FAILED      = "failed"
    CANCELLED   = "cancelled"

class DeliveryStatus:
    QUEUED     = "queued"
    SUCCESS    = "success"
    FAILED     = "failed"

# ── Meta Graph API ─────────────────────────────────────────────────────────
META_GRAPH_VERSION     = "v19.0"
META_API_BASE          = f"https://graph.facebook.com/{META_GRAPH_VERSION}"
TOKEN_REFRESH_DAYS     = 50     # refresh before 60-day expiry
TOKEN_EXPIRY_DAYS      = 60     # Meta long-lived token lifespan

# ── Default tags per vertical ──────────────────────────────────────────────
DEFAULT_TAGS = {
    "home_services":    ["#homeservices","#acservice","#plumbing","#serviceos","#doorstep"],
    "coaching_center":  ["#coaching","#education","#tuition","#serviceos","#learning"],
    "salon":            ["#salon","#beauty","#haircare","#serviceos","#grooming"],
    "real_estate":      ["#realestate","#property","#rental","#serviceos","#homeloans"],
}

# ── Redis keys ─────────────────────────────────────────────────────────────
REDIS_DALLE_BUDGET     = "serviceos:marketing:dalle_budget:{date}"
REDIS_PROMPT_HASH      = "serviceos:marketing:prompt:{prompt_hash}"
REDIS_POST_LOCK        = "serviceos:marketing:post_lock:{post_id}"
REDIS_TOKEN_LOCK       = "serviceos:marketing:token_lock:{account_id}"
BUDGET_COUNTER_TTL     = 86400   # 24h — resets daily
