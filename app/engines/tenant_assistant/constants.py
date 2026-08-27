"""Tenant AI Assistant — constants, tool specs and the answering contract.

Design rules that the rest of the engine enforces:

  * The assistant answers ONLY from retrieved help-centre content and from
    tenant-scoped tool results. The LLM is a renderer, never a source.
  * Every tool is read-only and scoped by the tenant_id taken from the JWT.
    No tool accepts a tenant id as an argument, so the model cannot ask for
    another business's data.
  * If retrieval and tools both come back empty, the LLM is never called at
    all — the configured no-answer message is returned and the tenant is
    offered a support ticket.
"""
from __future__ import annotations

ENGINE_ID = "tenant_assistant"

# ── option action types ──────────────────────────────────────────────────────
ACTION_ARTICLE = "article"   # target = article slug        → render one article
ACTION_TOPIC   = "topic"     # target = product_area        → list that area
ACTION_TOOL    = "tool"      # target = tool name           → run a tenant tool
ACTION_PROMPT  = "prompt"    # target = canned question     → full ask pipeline
ACTION_LINK    = "link"      # target = portal route        → deep link
ACTION_TICKET  = "ticket"    # target = None                → escalation form

ACTION_TYPES = [ACTION_ARTICLE, ACTION_TOPIC, ACTION_TOOL,
                ACTION_PROMPT, ACTION_LINK, ACTION_TICKET]

# ── message resolutions (drives admin analytics + auto-escalation) ───────────
RES_ANSWERED     = "answered"
RES_PARTIAL      = "partial"
RES_NO_ANSWER    = "no_answer"
RES_OUT_OF_SCOPE = "out_of_scope"
RES_ESCALATED    = "escalated"
RES_RATE_LIMITED = "rate_limited"
UNRESOLVED = {RES_NO_ANSWER, RES_OUT_OF_SCOPE}

SESSION_ACTIVE    = "active"
SESSION_ESCALATED = "escalated"
SESSION_CLOSED    = "closed"

ROLE_USER      = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM    = "system"

# ── the group headings shown in the options panel ────────────────────────────
GROUP_LABELS = {
    "getting_started":  "Getting started",
    "services_pricing": "Services & pricing",
    "bookings_jobs":    "Bookings & jobs",
    "team_access":      "Team & access",
    "finance_credits":  "Money & credits",
    "account_security": "Account & security",
    "support":          "Support",
}
GROUP_ORDER = list(GROUP_LABELS)

# ── portal deep links the assistant is allowed to emit ───────────────────────
# The model never invents a URL; it may only reference a key from this map.
# Every entry is a route that really exists in frontend/tenant-portal/app.
# Verified against the router on 2026-08-18 — a deep link to a page that 404s
# turns one support question into two, so this map is checked, not guessed.
PORTAL_ROUTES = {
    "dashboard":     ("/dashboard",                        "Dashboard"),
    "services":      ("/home-services/services",           "Services & pricing"),
    "coverage":      ("/business/coverage-hours",          "Coverage & hours"),
    "bookings":      ("/home-services/bookings-jobs",      "Bookings & jobs"),
    "jobs":          ("/jobs",                             "Jobs"),
    "dispatch":      ("/home-services/dispatch",           "Dispatch"),
    "team":          ("/home-services/team",               "Team"),
    "documents":     ("/business/verification-documents",  "Verification documents"),
    "finance":       ("/home-services/finance",            "Finance"),
    "package":       ("/home-services/finance",            "Finance & credits"),
    "credits":       ("/finance/usage-credit-ledger",      "Usage credits"),
    "reviews":       ("/home-services/reviews",            "Reviews"),
    "complaints":    ("/home-services/complaints",         "Complaints"),
    "notifications": ("/notifications",                    "Notifications"),
    "onboarding":    ("/onboarding-status",                "Onboarding status"),
    "support":       ("/help-support",                     "Help & Support"),
    "requests":      ("/help-support?tab=requests",        "My requests"),
    "account":       ("/account",                          "Account"),
}

# ── tool registry metadata ───────────────────────────────────────────────────
# `name` is matched to TenantAssistantTools._tool_<name>. Admins choose which
# of these the assistant may call; anything not in the config allowlist is
# never advertised to the model and is rejected if hallucinated.
TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": ("Search the ServiceOS help centre for how-to guides and "
                            "troubleshooting steps. Use for any 'how do I' question."),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What the user is trying to do"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_readiness_snapshot",
            "description": ("Current go-live readiness of THIS business: account status, "
                            "plan, team size, whether any jobs exist. Use for 'where do I "
                            "stand', 'what is pending', 'why can't I take bookings'."),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_profile",
            "description": ("This business's profile: name, account status, plan, health "
                            "band, vertical, activation date."),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_summary",
            "description": "Counts of this business's jobs by stage, plus upcoming scheduled work.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_summary",
            "description": "How many staff and technicians this business has, and how many are active.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_open_requests",
            "description": "This business's open support requests with ServiceOS, newest first.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_platform_status",
            "description": "Whether ServiceOS itself is healthy or has an active incident.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_announcements",
            "description": "Recent ServiceOS announcements relevant to provider businesses.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
TOOL_NAMES = [t["function"]["name"] for t in TOOL_SPECS]

# ── never leak these out of a tool result, whatever the query ────────────────
FORBIDDEN_OUTPUT_KEYS = {
    "commission", "commission_rate", "platform_fee", "platform_margin",
    "internal_note", "password", "password_hash", "secret", "api_key",
    "credentials", "gateway_secret", "webhook_secret",
}

# ── refusal triggers checked BEFORE any LLM call ─────────────────────────────
# Cheap, deterministic scope guard. Anything matching here is answered with the
# configured out_of_scope_message and never reaches DeepSeek.
OUT_OF_SCOPE_PATTERNS = [
    "source code", "sourcecode", "codebase", "repository", "github",
    "database schema", "db schema", "table structure", "sql query",
    "run sql", "drop table", "select * from", "migration file",
    "api key", "secret key", "env file", ".env", "environment variable",
    "server ip", "ssh", "deployment", "docker", "kubernetes",
    "your prompt", "system prompt", "your instructions", "ignore previous",
    "other tenant", "another tenant", "other business", "competitor data",
    "all tenants", "every tenant", "platform revenue", "how much does serviceos earn",
]

# ── prompts ──────────────────────────────────────────────────────────────────
CONTEXT_HEADER = (
    "CONTEXT — the ONLY facts you may use. If the answer is not here, say you "
    "do not have it documented and offer a support ticket.\n"
)
NO_CONTEXT_SENTINEL = "__NO_CONTEXT__"

MAX_HISTORY_TURNS = 6      # user+assistant pairs replayed into the LLM
MAX_QUESTION_CHARS = 1000
MAX_TRANSCRIPT_CHARS = 4000

DEFAULT_TICKET_SUBJECT = "Assistant could not resolve: {topic}"
