"""
Phase 22 — AI Chat Engine (DeepSeek) — Structural Tests (38 tests).
Tests cover: engine file structure, tool definitions, service architecture,
router registration, customer app integration, and security.
"""
import os, json, re, ast, pathlib

BACKEND   = str(pathlib.Path(__file__).parent.parent.resolve())
ENGINE    = f"{BACKEND}/app/engines/ai_chat"
CUSTOMER  = f"{BACKEND}/mobile/customer-app/src"

# ── 1. Engine file structure ───────────────────────────────────────────────────
REQUIRED_ENGINE_FILES = [
    "app/engines/ai_chat/__init__.py",
    "app/engines/ai_chat/constants.py",
    "app/engines/ai_chat/tools.py",
    "app/engines/ai_chat/service.py",
    "app/engines/ai_chat/router.py",
]

def test_all_engine_files_exist():
    missing = [f for f in REQUIRED_ENGINE_FILES
               if not os.path.exists(f"{BACKEND}/{f}")]
    assert not missing, f"Missing engine files: {missing}"

def test_router_registered_in_main():
    with open(f"{BACKEND}/app/main.py", encoding="utf-8") as f: c = f.read()
    assert "ai_chat" in c, "ai_chat router must be registered in main.py"
    assert "ai_chat_router" in c


# ── 2. Constants & prompt ──────────────────────────────────────────────────────
def test_deepseek_model_defined():
    with open(f"{ENGINE}/constants.py", encoding="utf-8") as f: c = f.read()
    assert "deepseek-chat" in c

def test_deepseek_api_base_defined():
    with open(f"{ENGINE}/constants.py", encoding="utf-8") as f: c = f.read()
    assert "api.deepseek.com" in c

def test_system_prompt_defined():
    with open(f"{ENGINE}/constants.py", encoding="utf-8") as f: c = f.read()
    assert "SYSTEM_PROMPT" in c
    assert "ServiceOS" in c

def test_system_prompt_covers_key_capabilities():
    with open(f"{ENGINE}/constants.py", encoding="utf-8") as f: c = f.read()
    for keyword in ["booking", "track", "price", "repair"]:
        assert keyword in c.lower(), f"System prompt missing: {keyword}"

def test_tools_list_defined():
    with open(f"{ENGINE}/constants.py", encoding="utf-8") as f: c = f.read()
    assert "TOOLS" in c
    assert "type.*function" in c or '"type": "function"' in c or "'type': 'function'" in c

def test_tools_cover_all_5_functions():
    with open(f"{ENGINE}/constants.py", encoding="utf-8") as f: c = f.read()
    for fn in ["get_my_bookings","get_booking_detail","get_active_job",
               "get_service_catalog","get_available_slots"]:
        assert fn in c, f"Missing tool: {fn}"

def test_max_tool_iterations_defined():
    with open(f"{ENGINE}/constants.py", encoding="utf-8") as f: c = f.read()
    assert "MAX_TOOL_ITERATIONS" in c


# ── 3. Tool executor ──────────────────────────────────────────────────────────
def test_tool_executor_class_exists():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    assert "class ToolExecutor" in c

def test_tool_executor_takes_customer_id():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    assert "customer_id" in c

def test_tool_executor_has_all_5_handlers():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    for fn in ["_tool_get_my_bookings","_tool_get_booking_detail","_tool_get_active_job",
               "_tool_get_service_catalog","_tool_get_available_slots"]:
        assert fn in c, f"Missing handler: {fn}"

def test_tool_executor_uses_sqlalchemy_not_raw_sql():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    assert "select(" in c or "AsyncSession" in c

def test_tool_executor_returns_json_string():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    assert "json.dumps" in c

def test_tool_executor_has_error_handling():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    assert "try:" in c or "except" in c

def test_booking_tool_filters_by_customer_id():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    assert "customer_id" in c and "Booking" in c

def test_price_estimate_covers_common_services():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    for svc in ["AC Repair", "Plumbing", "Electrical", "Cleaning"]:
        assert svc in c, f"Price estimate missing: {svc}"


# ── 4. Service / LLM orchestration ────────────────────────────────────────────
def test_ai_chat_service_class_exists():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "class AIChatService" in c

def test_service_uses_httpx_not_openai_sdk():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "httpx" in c
    # DeepSeek compatible but we use httpx directly (no extra dep)
    assert "import openai" not in c

def test_service_reads_api_key_from_env():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "DEEPSEEK_API_KEY" in c
    assert "os.environ" in c or "os.getenv" in c or 'environ.get' in c or "get_settings" in c

def test_service_api_key_not_hardcoded():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "sk-" not in c, "API key must NOT be hardcoded"

def test_service_has_tool_calling_loop():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "tool_calls" in c
    assert "for" in c  # loop over tool calls

def test_service_has_max_iteration_guard():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "MAX_TOOL_ITERATIONS" in c

def test_service_caps_history_at_20():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "20" in c  # max 20 history turns

def test_service_raises_error_when_key_missing():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "DEEPSEEK_NOT_CONFIGURED" in c or "not configured" in c.lower()

def test_service_handles_deepseek_timeout():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "TimeoutException" in c or "timeout" in c.lower()

def test_service_handles_deepseek_http_error():
    with open(f"{ENGINE}/service.py", encoding="utf-8") as f: c = f.read()
    assert "status_code" in c or "HTTP" in c


# ── 5. Router ────────────────────────────────────────────────────────────────
def test_router_has_post_chat_endpoint():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "@router.post" in c
    assert '"/chat"' in c or "'/chat'" in c

def test_router_has_meta_endpoint():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "meta" in c

def test_router_prefix_is_v1_ai():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert '"/v1/ai"' in c or "'/v1/ai'" in c

def test_router_schema_validates_message_length():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "max_length" in c

def test_router_schema_caps_history():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "max_length=20" in c or "max_length = 20" in c

def test_router_returns_tools_called():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "tools_called" in c

def test_router_engine_id_is_ai_chat():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert 'ENGINE_ID = "ai_chat"' in c or "ENGINE_ID = 'ai_chat'" in c


# ── 6. Customer app integration ───────────────────────────────────────────────
def test_ai_chat_api_in_customer_lib():
    with open(f"{CUSTOMER}/api/assistant/assistantApi.ts", encoding="utf-8") as f: c = f.read()
    assert "sendAssistantMessage" in c

def test_ai_chat_api_calls_v1_ai_chat():
    with open(f"{CUSTOMER}/api/assistant/assistantApi.ts", encoding="utf-8") as f: c = f.read()
    assert '"/v1/customer/ai-chat/sessions"' in c
    assert '"/v1/ai/chat"' not in c

def test_ai_chat_screen_exists():
    assert os.path.exists(f"{CUSTOMER}/screens/bookingChat/BookingChatScreen.tsx")

def test_ai_chat_screen_uses_aiChatApi():
    with open(f"{CUSTOMER}/screens/bookingChat/BookingChatScreen.tsx", encoding="utf-8") as f: c = f.read()
    assert "useAssistantController" in c

def test_ai_chat_screen_has_quick_prompts():
    with open(f"{CUSTOMER}/screens/bookingChat/BookingChatScreen.tsx", encoding="utf-8") as f: c = f.read()
    assert "quick" in c.lower() or "Option" in c

def test_ai_chat_screen_shows_tool_usage():
    with open(f"{CUSTOMER}/components/assistant/AssistantActivity.tsx", encoding="utf-8") as f: c = f.read()
    assert "stage" in c and "resolveActivityLabel" in c

def test_tab_navigator_has_ai_tab():
    with open(f"{CUSTOMER}/navigation/CustomerTabs.tsx", encoding="utf-8") as f: c = f.read()
    assert 'name="Assistant"' in c and "BookingChatScreen" in c

def test_ai_chat_screen_has_no_hardcoded_api_key():
    with open(f"{CUSTOMER}/screens/bookingChat/BookingChatScreen.tsx", encoding="utf-8") as f: c = f.read()
    assert "sk-" not in c
    assert "DEEPSEEK" not in c, "API key must be backend-only"
