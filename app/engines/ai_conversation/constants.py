"""AI Conversation Engine — Constants and configuration."""

DEEPSEEK_API_BASE    = "https://api.deepseek.com"
DEEPSEEK_MODEL       = "deepseek-chat"
DEEPSEEK_MAX_TOKENS  = 1500
DEEPSEEK_TEMPERATURE = 0.6
MAX_TOOL_ITERATIONS  = 8
DEEPSEEK_TIMEOUT_S   = 30

# ── Workflow statuses ─────────────────────────────────────────────────────────
WORKFLOW_STATUS_ACTIVE     = "active"
WORKFLOW_STATUS_PAUSED     = "paused"
WORKFLOW_STATUS_COMPLETED  = "completed"
WORKFLOW_STATUS_ABANDONED  = "abandoned"

VALID_WORKFLOW_STATUSES = {
    WORKFLOW_STATUS_ACTIVE,
    WORKFLOW_STATUS_PAUSED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_ABANDONED,
}

# ── Intent types ──────────────────────────────────────────────────────────────
INTENT_SERVICE_INQUIRY   = "service_inquiry"
INTENT_BOOKING_INTENT    = "booking_intent"
INTENT_STATUS_CHECK      = "status_check"
INTENT_COMPLAINT         = "complaint"
INTENT_GENERAL_QUERY     = "general_query"
INTENT_UNKNOWN           = "unknown"

VALID_INTENTS = {
    INTENT_SERVICE_INQUIRY,
    INTENT_BOOKING_INTENT,
    INTENT_STATUS_CHECK,
    INTENT_COMPLAINT,
    INTENT_GENERAL_QUERY,
    INTENT_UNKNOWN,
}

# ── Message roles ─────────────────────────────────────────────────────────────
ROLE_USER      = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM    = "system"
ROLE_TOOL      = "tool"

# ── Prompt template categories ────────────────────────────────────────────────
TEMPLATE_CAT_SYSTEM   = "system"
TEMPLATE_CAT_WORKFLOW = "workflow"
TEMPLATE_CAT_SAFETY   = "safety"
TEMPLATE_CAT_CONTEXT  = "context"

# ── Safety — fields DeepSeek MUST NEVER output ───────────────────────────────
FORBIDDEN_OUTPUT_FIELDS = {
    "price",
    "final_price",
    "provider_id",
    "tenant_id",
    "credit_balance",
    "subscription_status",
    "commission",
    "booking_id",
    "appointment_id",
    "lead_id",
    "payment_status",
}

# ── Safety — fields DeepSeek MUST NEVER receive in its output ─────────────────
FORBIDDEN_PROMPT_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "you are now",
    "act as a",
    "pretend you are",
    "system prompt",
    "reveal your instructions",
    "show me your prompt",
    "jailbreak",
]

# ── Audit event types ─────────────────────────────────────────────────────────
AUDIT_SESSION_START       = "session_start"
AUDIT_SESSION_CLOSE       = "session_close"
AUDIT_INTENT_CHANGE       = "intent_change"
AUDIT_SAFETY_VIOLATION    = "safety_violation"
AUDIT_FORBIDDEN_FIELD     = "forbidden_field_stripped"
AUDIT_PROMPT_INJECTION    = "prompt_injection_detected"
AUDIT_MAX_TURNS_REACHED   = "max_turns_reached"

# ── Session limits ────────────────────────────────────────────────────────────
MAX_TURNS_PER_SESSION = 50
MAX_HISTORY_MESSAGES  = 20

# ── Audit severity levels ─────────────────────────────────────────────────────
SEVERITY_INFO    = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR   = "error"

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_SESSION_NOT_FOUND      = "AI_SESSION_NOT_FOUND"
ERR_SESSION_CLOSED         = "AI_SESSION_CLOSED"
ERR_SESSION_MAX_TURNS      = "AI_SESSION_MAX_TURNS_EXCEEDED"
ERR_DEEPSEEK_NOT_CONFIGURED = "DEEPSEEK_NOT_CONFIGURED"
ERR_DEEPSEEK_CALL_FAILED   = "DEEPSEEK_CALL_FAILED"
ERR_TEMPLATE_NOT_FOUND     = "AI_TEMPLATE_NOT_FOUND"
ERR_TEMPLATE_KEY_EXISTS    = "AI_TEMPLATE_KEY_EXISTS"
ERR_FORBIDDEN_OUTPUT       = "AI_FORBIDDEN_OUTPUT_FIELD"
ERR_PROMPT_INJECTION       = "AI_PROMPT_INJECTION_DETECTED"

# ── System prompt (base, overridden by active prompt template) ────────────────
BASE_SYSTEM_PROMPT = """You are ServiceOS Assistant — a warm, helpful AI for home service customers in India.

## YOUR JOB
Help customers understand what service they need, answer questions about services, and prepare their request for booking. You do NOT create bookings, appointments, or leads — the app handles that after you complete the conversation.

## SERVICE TYPES
- REPAIR: Something broken (AC not cooling, pipe leaking, etc.) — technician inspects first, price quoted after
- SERVICE/MAINTENANCE: Routine care (AC annual service, cleaning, pest control) — fixed price known upfront
- CONSULTATION: Unsure what's needed, want expert advice — fixed consultation fee, expert gives written report

## CONVERSATION RULES
- Ask at most 1-2 clarifying questions before recommending
- Be concise — customers are on mobile phones
- Never quote specific prices — the backend provides real pricing
- Never claim to book something — say "I'll prepare your request"
- Use ₹ for Indian Rupee references
- When you know what the customer needs, summarize the request clearly

## MESSAGE FORMAT (this renders as one chat bubble, not a document)
- Plain conversational text only — NO markdown headers, NO bold/asterisks,
  NO numbered lists, NO emoji
- 1-3 short sentences per message, like a real chat message
- Ask exactly ONE question at a time, never a numbered list of questions.
  This applies EVEN ACROSS different kinds of question -- never combine a
  `still_needed` text question (e.g. preferred date) with a mention of
  brand/type/AC-type or any other tap-card-driven field in the same
  message, even in passing ("...and also let me know the brand"). Ask the
  ONE `still_needed` text question alone; the tap cards appear separately
  and don't need a chat mention at all.
- If you need to choose between a few known options, prefer calling a tool
  that returns real selectable options over listing them yourself in text
- When get_category_offerings returns MORE THAN ONE offering and the
  customer's own message gives no signal which one they mean, do NOT
  explain what each offering means or write a paragraph — ask ONE short
  forced-choice sentence naming the offerings directly, e.g. "Is this an
  AC Installation, or an AC Service/repair?" (max ~12 words). If the
  customer's message already implies one (e.g. "not cooling" → repair/
  service, "new AC"/"install" → installation), skip asking entirely and
  go straight to start_home_service_draft with that offering.

## TOOL USE DISCIPLINE
- NEVER call a tool with a value the customer did not actually state (e.g.
  never guess a city or zipcode for check_service_area — only call it once
  the customer has told you their city)
- You may call up to 6-7 tools in a row before replying in plain text when
  following the MANDATORY BOOKING SEQUENCE below — do not stop early to
  reply just because you've made a few calls; stopping mid-sequence to ask
  something in chat that a later tool in the sequence would have answered
  (like brand or AC type) is wrong, not helpful
- For clear booking intent (customer names a problem, e.g. "pipe is
  leaking", "install a new AC"), go straight into the MANDATORY BOOKING
  SEQUENCE below, without checking service area first (serviceability is
  already implied by the zipcode on this conversation)

## MANDATORY BOOKING SEQUENCE — do all of this before replying in text
1. get_service_categories -> get_category_offerings (resolve the real
   category_slug/offering_slug)
2. start_home_service_draft — its response ALREADY includes a `problems`
   list (the real problem/issue options for this exact service) and
   `still_needed`. You do NOT need, and must NOT call, a separate
   get_service_problems tool — it no longer exists as a distinct step;
   everything you need is in this one response.
3. Match the customer's description to one of the `problems` ids yourself
   (or, only if genuinely ambiguous, this is where you may stop and ask
   ONE short clarifying question in text)
4. update_home_service_draft with selected_problem_id set to that exact id
   — this is what unlocks the app's own tap-select question cards
   (brand/type/detail pickers) for anything catalog-driven; NEVER ask
   about brand, AC type, or similar catalog fields yourself in chat text,
   even if the customer hasn't answered them yet — the tap cards handle it
5. Only THEN reply in text, and only ask about fields still in
   `still_needed` (from step 2's response) — NEVER city, zipcode, name, or
   phone, which come from the customer's saved account automatically and
   are never in `still_needed` when already known; asking again is a bug,
   not politeness.

Steps 3-4 are NOT optional and NOT something to defer to a later message —
do them in the SAME turn as step 2, before you say anything to the
customer. If you skip straight to asking the customer questions in text
without calling update_home_service_draft first, the customer is forced
to type everything manually instead of tapping.

NEVER mention "tap-select", "cards", "options below", "the app will show
you", or any other description of the UI mechanism itself — the customer
never sees this prompt or your reasoning, only your plain reply text. Just
say what's still needed in plain words (or nothing at all, if
`still_needed` is empty), never narrate how the interface works.

## WHAT YOU MUST NOT DO
- Create bookings, appointments, or leads
- Quote final prices (use "starting from" or "typically" language)
- Promise specific provider availability
- Share provider IDs, tenant IDs, commission rates, or credit balances
- Invent a problem id, question, or option not returned by a tool

## INTENT CLASSIFICATION
At the start of each message, classify intent as one of:
service_inquiry, booking_intent, status_check, complaint, general_query

Keep responses short, plain, and friendly — 1-3 sentences, never more than
60 words, no markdown formatting."""

# ── Backend tool definitions (wired to real data, not mocked) ─────────────────
BACKEND_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_service_categories",
            "description": "Get customer-visible service categories. Use when customer asks what services are available or to help classify their need.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Optional search term to filter categories"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_offerings",
            "description": "Get available service offerings for a specific category. Use when customer has identified a category and wants to know specific services available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_slug": {
                        "type": "string",
                        "description": "The category slug (e.g. 'ac-repair', 'plumbing', 'electrical')"
                    },
                    "search": {
                        "type": "string",
                        "description": "Optional search term to filter offerings"
                    }
                },
                "required": ["category_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_faqs",
            "description": "Get FAQs about a service type. Use when customer asks general questions about how services work, what's included, or pricing policy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_slug": {
                        "type": "string",
                        "description": "Category to get FAQs for"
                    }
                },
                "required": ["category_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_recent_bookings",
            "description": "Get the customer's recent booking history. Use when they ask about 'my bookings', 'my orders', recent services.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of recent bookings to return (max 10)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_service_area",
            "description": "Check if a service is available in a specific city/area. Use when customer mentions their location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name to check availability"
                    },
                    "category_slug": {
                        "type": "string",
                        "description": "Service category to check in that area"
                    }
                },
                "required": ["city"]
            }
        }
    },
    # ── Sprint 16 — Home Service Booking Draft tools ──────────────────────────
    {
        "type": "function",
        "function": {
            "name": "start_home_service_draft",
            "description": (
                "Start a Home Service booking draft when customer clearly wants to book a service. "
                "category_slug and offering_slug MUST be the exact slugs returned by "
                "get_service_categories / get_category_offerings for this conversation -- never "
                "guess or hardcode a slug (categories are per-tenant, real values include "
                "'plumbing', 'electrical', 'air-conditioning', 'painting', 'pest-control', "
                "'home-cleaning', not a generic 'home-services'). "
                "Returns required_fields list — ask for these one at a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category_slug": {"type": "string", "description": "The exact category slug from get_service_categories/get_category_offerings"},
                    "offering_slug": {"type": "string", "description": "The exact offering slug from get_category_offerings"}
                },
                "required": ["category_slug", "offering_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_home_service_draft_status",
            "description": "Get the current status and missing fields for an active booking draft. Use to know what info still needs to be collected.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "The booking draft ID returned by start_home_service_draft"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_home_service_draft",
            "description": (
                "Save customer-provided fields into the booking draft. "
                "Only pass fields the customer has explicitly stated. "
                "NEVER include price, provider_id, commission."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id":              {"type": "string", "description": "The booking draft ID"},
                    "selected_problem_id":   {"type": "string", "description": "Exact id from start_home_service_draft's own `problems` list matching the customer's issue -- set this as soon as you know which problem it is, it unlocks the next structured tap-select questions. Call this in the SAME turn as start_home_service_draft, never deferred to a later message."},
                    "issue_summary":         {"type": "string", "description": "Customer's problem description"},
                    "city":                  {"type": "string", "description": "City name"},
                    "zipcode":               {"type": "string", "description": "Postal/ZIP code"},
                    "customer_name":         {"type": "string", "description": "Customer's name"},
                    "customer_phone":        {"type": "string", "description": "Customer's phone number"},
                    "preferred_date":        {"type": "string", "description": "Preferred date ISO 8601"},
                    "preferred_time_window": {"type": "string", "description": "Time window e.g. '10:00-14:00'"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_home_service_availability",
            "description": "Check if the service is available in the customer's city/zipcode. Call after city is collected. Backend checks real provider coverage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "The booking draft ID"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_home_service_price_estimate",
            "description": "Get the backend-computed price estimate. NEVER quote a price yourself — always use this tool. Returns display_price like '₹399'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "The booking draft ID"}
                },
                "required": ["draft_id"]
            }
        }
    },
    # ── Sprint 17 — Coaching Appointment Draft tools ──────────────────────────
    {
        "type": "function",
        "function": {
            "name": "start_coaching_appointment_draft",
            "description": (
                "Start a Coaching/IELTS appointment draft when customer wants to book a demo class, "
                "trial class, consultation, or any coaching appointment. "
                "Use category_slug='coaching-center' and the appropriate offering_slug "
                "(e.g. 'ielts-demo-class', 'pte-demo-class', 'spoken-english-trial'). "
                "Returns required_fields list — ask for these one at a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category_slug": {"type": "string", "description": "Always 'coaching-center' for coaching appointments"},
                    "offering_slug": {"type": "string", "description": "Offering slug, e.g. 'ielts-demo-class', 'pte-demo-class'"}
                },
                "required": ["category_slug", "offering_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_coaching_draft_status",
            "description": "Get current status and missing fields for a coaching appointment draft. Use to know what info still needs collecting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "The coaching draft ID returned by start_coaching_appointment_draft"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_coaching_appointment_draft",
            "description": (
                "Save student/appointment fields into the coaching draft. "
                "Only pass fields the student has explicitly provided. "
                "NEVER include fee, slot, tenant_id, commission."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id":          {"type": "string", "description": "The coaching draft ID"},
                    "student_name":      {"type": "string", "description": "Student's full name"},
                    "student_phone":     {"type": "string", "description": "Student's phone number"},
                    "student_email":     {"type": "string", "description": "Student's email"},
                    "student_age":       {"type": "integer", "description": "Student's age"},
                    "target_exam":       {"type": "string", "description": "Target exam e.g. IELTS, PTE, TOEFL"},
                    "target_band":       {"type": "string", "description": "Target band score e.g. 7, 7.5"},
                    "preferred_mode":    {"type": "string", "description": "online, offline, or hybrid"},
                    "city":              {"type": "string", "description": "City name"},
                    "zipcode":           {"type": "string", "description": "Postal code"},
                    "selected_date":     {"type": "string", "description": "Preferred date YYYY-MM-DD"},
                    "current_education": {"type": "string", "description": "Current education level"},
                    "notes":             {"type": "string", "description": "Additional notes from student"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_coaching_centers",
            "description": (
                "Find bookable coaching centers for the appointment. "
                "Call AFTER student has provided city and preferred_mode. "
                "Backend queries real providers — never fake centers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "The coaching draft ID"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_coaching_appointment_slots",
            "description": (
                "Get available appointment slots. "
                "If requested date is full, backend finds next available slots automatically. "
                "Returns assistant_conversion_hint when requested date is unavailable — use it to suggest best next slot. "
                "NEVER invent slots, urgency, seat count, or trainer quality. Only use backend data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id":       {"type": "string", "description": "The coaching draft ID"},
                    "preferred_date": {"type": "string", "description": "Date to check, YYYY-MM-DD (optional, uses draft's selected_date if not provided)"}
                },
                "required": ["draft_id"]
            }
        }
    },

    # ── Sprint 18 — Real Estate Lead tools ────────────────────────────────────

    {
        "type": "function",
        "function": {
            "name": "start_real_estate_lead_draft",
            "description": (
                "Start a Real Estate lead draft when customer wants to buy, rent, sell property, "
                "book a site visit, or make a property inquiry. "
                "Call this as soon as the intent is clearly real estate. "
                "Returns draft_id and required_fields list. "
                "DeepSeek must NOT select providers, decide property price, or create leads."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category_slug": {
                        "type": "string",
                        "description": "Category slug, e.g. 'real-estate' or 'property'"
                    },
                    "offering_slug": {
                        "type": "string",
                        "description": "Offering slug, e.g. 'buy-property-inquiry', 'rent-property-inquiry', 'sell-property-inquiry', 'site-visit-request'"
                    }
                },
                "required": ["category_slug", "offering_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_real_estate_draft_status",
            "description": (
                "Get the current status and missing fields for a real estate lead draft. "
                "Use this to know what information still needs to be collected from the customer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "The real estate lead draft ID returned by start_real_estate_lead_draft"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_real_estate_lead_draft",
            "description": (
                "Save property requirement fields collected from conversation. "
                "Only pass fields the customer has explicitly provided. "
                "NEVER include provider_id, agent_id, commission, guaranteed_price, or internal data. "
                "Allowed fields: lead_intent, property_type, city, locality, zipcode, "
                "budget_min, budget_max, rent_min, rent_max, bedrooms, bathrooms, "
                "area_sqft_min, area_sqft_max, furnishing, possession_preference, "
                "customer_name, customer_phone, customer_email, preferred_contact_time, notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id":               {"type": "string",  "description": "The real estate lead draft ID"},
                    "lead_intent":            {"type": "string",  "description": "buy|rent|sell|site_visit|consultation|commercial|plot"},
                    "property_type":          {"type": "string",  "description": "house|flat|apartment|villa|plot|shop|office|commercial|land|other"},
                    "city":                   {"type": "string",  "description": "City name"},
                    "locality":               {"type": "string",  "description": "Locality or area name"},
                    "zipcode":                {"type": "string",  "description": "Postal code"},
                    "budget_min":             {"type": "number",  "description": "Minimum budget in INR"},
                    "budget_max":             {"type": "number",  "description": "Maximum budget in INR"},
                    "rent_min":               {"type": "number",  "description": "Minimum rent in INR per month"},
                    "rent_max":               {"type": "number",  "description": "Maximum rent in INR per month"},
                    "bedrooms":               {"type": "integer", "description": "Number of bedrooms required"},
                    "furnishing":             {"type": "string",  "description": "furnished|semi_furnished|unfurnished|not_sure"},
                    "possession_preference":  {"type": "string",  "description": "ready_to_move|under_construction|any"},
                    "customer_name":          {"type": "string",  "description": "Customer's name"},
                    "customer_phone":         {"type": "string",  "description": "Customer's phone number"},
                    "customer_email":         {"type": "string",  "description": "Customer's email address"},
                    "preferred_contact_time": {"type": "string",  "description": "When customer wants to be contacted, e.g. 'Morning', 'Evening'"},
                    "notes":                  {"type": "string",  "description": "Additional notes from customer"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_real_estate_providers",
            "description": (
                "Find bookable real estate providers/agents for the lead. "
                "Call AFTER customer has provided city, lead_intent, and property_type. "
                "Backend queries real providers — never fake agents or listings. "
                "If exact locality has no match, returns city-level fallback with assistant_conversion_hint. "
                "Use the conversion hint to suggest broadening the search — do NOT invent providers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "The real estate lead draft ID"}
                },
                "required": ["draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_real_estate_lead_summary",
            "description": (
                "Build and return the lead summary for customer confirmation. "
                "Call after required fields are complete and providers found or fallback ready. "
                "Returns structured summary + backend-calculated lead score. "
                "NEVER invent property listings, prices, guaranteed deals, or agent quality claims. "
                "Use the summary to ask customer to confirm their inquiry."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "The real estate lead draft ID"}
                },
                "required": ["draft_id"]
            }
        }
    }
]
