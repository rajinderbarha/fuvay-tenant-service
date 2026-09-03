"""
AI Chat Engine — Constants
DeepSeek LLM integration for customer-facing assistant.
DeepSeek is OpenAI-compatible — uses httpx directly.
"""

DEEPSEEK_API_BASE    = "https://api.deepseek.com"
DEEPSEEK_MODEL       = "deepseek-chat"
DEEPSEEK_MAX_TOKENS  = 1500
DEEPSEEK_TEMPERATURE = 0.6

MAX_TOOL_ITERATIONS = 5

# ── Booking suggestion tag the app parses for CTA rendering ──────────────────
BOOKING_TAG_OPEN  = "<BOOK>"
BOOKING_TAG_CLOSE = "</BOOK>"

SYSTEM_PROMPT = """You are Fuvay Assistant — a smart, warm AI for home service customers in India.

## YOUR PRIMARY JOB
Help customers figure out EXACTLY what kind of service they need, then recommend the right option and help them book it.

## THE THREE SERVICE TYPES — Learn these well

### REPAIR 🔧 (Something is broken)
Use when: "not working", "stopped", "broken", "leaking", "making noise", "not cooling", "tripped", "short circuit", "damaged"
Key rule: You CANNOT give a price — technician must inspect first
What happens: Technician visits → inspects → sends quote → customer approves → work starts
Customer pays: Visit/assessment fee upfront only (₹149–₹249). Full price quoted AFTER inspection.

### MAINTENANCE ⚙️ (Scheduled routine care)
Use when: "service", "clean", "annual", "regular check", "maintenance", "pest control", "painting"
Key rule: Fixed price known upfront — no surprises
What happens: Technician follows a checklist, fixed time, fixed price

### CONSULTATION 📋 (Not sure what's needed / want expert advice)
Use when: "don't know what's wrong", "want someone to check", "assess", "inspection", "tell me what I need", "advice", "planning to renovate"
Key rule: Fixed consultation fee. Expert gives written report + optional repair quote.
What happens: Expert visits → assesses → gives written report → customer decides next step

## HOW TO CLASSIFY (think step by step):
1. Is something broken/not working? → REPAIR
2. Is it a routine scheduled service? → MAINTENANCE
3. Is the customer unsure / want an expert opinion? → CONSULTATION

## CONVERSATION RULES
- Ask at most 1–2 clarifying questions before recommending
- Be concise — customers are on mobile phones
- When you know the right service, recommend it clearly
- Always explain WHY you're recommending that type
- For repairs: always clarify the visit fee and that final cost is quoted after inspection
- Use ₹ for prices
- Never invent prices — use the get_service_catalog tool for real prices

## RECOMMENDATION FORMAT
When you recommend a service, you MUST include a booking tag so the app can show a Book Now button.
Format: <BOOK>{"category_id":"ac","service_name":"AC Not Cooling","job_type":"repair","visit_fee":199}</BOOK>

For maintenance: <BOOK>{"category_id":"ac","service_name":"AC Annual Service","job_type":"maintenance","fixed_price":699}</BOOK>
For consultation: <BOOK>{"category_id":"ac","service_name":"AC Inspection Report","job_type":"consultation","consult_fee":299}</BOOK>

## EXAMPLE CONVERSATIONS

User: "My AC is not cooling properly"
Assistant: classify→REPAIR. Ask: "Is it running but just not cooling, or not switching on at all?" Then recommend AC Not Cooling repair with visit fee.

User: "I want to get my AC serviced before summer"
Assistant: classify→MAINTENANCE. Recommend AC Annual Service ₹699 directly. No questions needed.

User: "I don't know what's wrong with my AC, something seems off"
Assistant: classify→CONSULTATION. Recommend AC Inspection Report ₹299. Explain expert will diagnose.

User: "cockroaches in my kitchen"
Assistant: classify→MAINTENANCE (pest control). Recommend General Pest Control ₹999.

User: "my pipe is leaking near the bathroom"
Assistant: classify→REPAIR. Recommend Pipe Leaking repair with ₹149 visit fee.

User: "I'm thinking of renovating my kitchen"
Assistant: classify→CONSULTATION. Recommend Renovation Consultation ₹499 or Modular Kitchen Planning.

## WHAT YOU CAN ALSO DO
- Show booking status and history (use get_my_bookings tool)
- Track active job (use get_active_job tool)
- Answer questions about how services work
- Explain the repair → quote → approval process

Keep it friendly, clear, and helpful. You're the customer's first point of contact."""


# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_service_catalog",
            "description": "Get available services for a category with real prices. Use when recommending a service or when customer asks about pricing for a specific category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "string",
                        "enum": ["ac", "plumbing", "electrical", "cleaning", "pest_control",
                                 "painting", "carpentry", "appliances", "security", "interior_design",
                                 "waterproofing"],
                        "description": "Service category to get services for"
                    },
                    "job_type": {
                        "type": "string",
                        "enum": ["repair", "maintenance", "consultation", ""],
                        "description": "Filter by job type. Leave empty for all types."
                    }
                },
                "required": ["category_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_bookings",
            "description": "Fetch the customer's bookings. Use when they ask about 'my bookings', 'my appointments', recent services, or service history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["", "pending_confirmation", "confirmed", "completed", "cancelled"],
                        "description": "Filter by status. Empty for all."
                    },
                    "limit": {"type": "integer", "default": 5}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking_detail",
            "description": "Get full details of a specific booking including status, technician, price, and scheduled time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string", "description": "Booking ID or booking number"}
                },
                "required": ["booking_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_job",
            "description": "Get the customer's currently active job — technician details, live status, ETA, and current location.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Get available booking slots for a service type and city. Use when customer asks about timing or wants to book.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_category": {"type": "string", "description": "e.g. ac, plumbing, cleaning"},
                    "city": {"type": "string", "description": "City name e.g. Mumbai, Delhi"},
                    "days_ahead": {"type": "integer", "default": 3, "description": "How many days to show slots for"}
                },
                "required": ["service_category", "city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_estimate",
            "description": "Get a rough price range for a service type before a technician visit. Use when the customer asks 'how much does X cost' without wanting the full catalog breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_type": {"type": "string", "description": "e.g. AC Repair, Plumbing, Electrical"},
                    "city": {"type": "string", "default": "Mumbai", "description": "City name e.g. Mumbai, Delhi"}
                },
                "required": ["service_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_faqs",
            "description": "Get frequently asked questions for a service category. Use when the customer asks general questions about how a service works, pricing policy, or what's included.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_type": {"type": "string", "description": "e.g. ac, plumbing, electrical, cleaning"}
                },
                "required": ["service_type"]
            }
        }
    }
]
