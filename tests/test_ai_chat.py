"""AI Chat Engine tests — system prompt, tools, classification, booking tag."""
import os, sys, pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.insert(0, BASE)
ENGINE = os.path.join(BASE, "app/engines/ai_chat")

def test_constants_file_exists():
    assert os.path.exists(f"{ENGINE}/constants.py")

def test_tools_file_exists():
    assert os.path.exists(f"{ENGINE}/tools.py")

def test_deepseek_model_set():
    from app.engines.ai_chat.constants import DEEPSEEK_MODEL
    assert DEEPSEEK_MODEL == "deepseek-chat"

def test_system_prompt_classifies_repair_keywords():
    from app.engines.ai_chat.constants import SYSTEM_PROMPT
    p = SYSTEM_PROMPT.lower()
    for kw in ["not working", "broken", "leaking", "not cooling"]:
        assert kw in p, f"Missing repair keyword: {kw}"

def test_system_prompt_classifies_maintenance_keywords():
    from app.engines.ai_chat.constants import SYSTEM_PROMPT
    p = SYSTEM_PROMPT.lower()
    for kw in ["service", "annual", "routine", "maintenance"]:
        assert kw in p, f"Missing maintenance keyword: {kw}"

def test_system_prompt_classifies_consultation_keywords():
    from app.engines.ai_chat.constants import SYSTEM_PROMPT
    p = SYSTEM_PROMPT.lower()
    for kw in ["don't know", "assess", "inspection", "advice"]:
        assert kw in p, f"Missing consultation keyword: {kw}"

def test_booking_tag_in_system_prompt():
    from app.engines.ai_chat.constants import SYSTEM_PROMPT, BOOKING_TAG_OPEN, BOOKING_TAG_CLOSE
    assert BOOKING_TAG_OPEN  in SYSTEM_PROMPT
    assert BOOKING_TAG_CLOSE in SYSTEM_PROMPT
    assert "category_id"  in SYSTEM_PROMPT
    assert "service_name" in SYSTEM_PROMPT
    assert "job_type"     in SYSTEM_PROMPT

def test_booking_tag_constants_defined():
    from app.engines.ai_chat.constants import BOOKING_TAG_OPEN, BOOKING_TAG_CLOSE
    assert BOOKING_TAG_OPEN  == "<BOOK>"
    assert BOOKING_TAG_CLOSE == "</BOOK>"

def test_tools_list_has_five_tools():
    from app.engines.ai_chat.constants import TOOLS
    assert len(TOOLS) >= 5

def test_tool_get_service_catalog_exists():
    from app.engines.ai_chat.constants import TOOLS
    names = [t["function"]["name"] for t in TOOLS]
    assert "get_service_catalog" in names

def test_tool_get_available_slots_exists():
    from app.engines.ai_chat.constants import TOOLS
    names = [t["function"]["name"] for t in TOOLS]
    assert "get_available_slots" in names

def test_tool_get_my_bookings_exists():
    from app.engines.ai_chat.constants import TOOLS
    names = [t["function"]["name"] for t in TOOLS]
    assert "get_my_bookings" in names

def test_service_catalog_covers_all_categories():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: src = f.read()
    for cat in ["ac", "plumbing", "electrical", "cleaning", "pest_control",
                "painting", "carpentry", "appliances", "interior_design"]:
        assert f'"{cat}"' in src, f"Category missing: {cat}"

def test_service_catalog_has_all_price_types():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: src = f.read()
    assert "visit_fee"   in src
    assert "fixed_price" in src
    assert "consult_fee" in src

def test_service_catalog_ac_has_repair_and_maintenance():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: src = f.read()
    assert "AC Not Cooling"   in src
    assert "AC Annual Service" in src
    assert "AC Inspection Report" in src

def test_available_slots_generates_dates():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: src = f.read()
    assert "timedelta" in src or "days_ahead" in src
    assert "available_slots" in src

def test_api_key_not_in_tools():
    with open(f"{ENGINE}/tools.py", encoding="utf-8") as f: c = f.read()
    assert "DEEPSEEK_API_KEY" not in c
    assert "api.deepseek.com" not in c

def test_system_prompt_mobile_friendly():
    from app.engines.ai_chat.constants import SYSTEM_PROMPT
    assert "mobile" in SYSTEM_PROMPT.lower()

def test_system_prompt_has_examples():
    from app.engines.ai_chat.constants import SYSTEM_PROMPT
    assert "AC is not cooling" in SYSTEM_PROMPT or "not cooling" in SYSTEM_PROMPT
    assert "cockroaches" in SYSTEM_PROMPT or "pest" in SYSTEM_PROMPT.lower()
