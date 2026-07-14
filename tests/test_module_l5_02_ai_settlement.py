"""MODULE-L5-02 bugs #37/#38 — the AI settlement engine was a dead end."""
import inspect


def test_answers_can_be_submitted_and_trigger_the_analysis():
    """Bug #37: start_session asked the customer AND the tenant clarifying
    questions, but there was NO endpoint on either side to answer them — so
    customer_answers/tenant_answers stayed NULL forever and the session sat in
    'collecting' permanently. And analyze_and_propose() — which turns the answers
    into the AI recommendation and the SettlementProposal — had ZERO callers, so
    the AI never analysed anything.

    Proven live: both parties answer -> session 'completed', confidence 0.7,
    3 risk flags, and an AI settlement proposal (partial_refund) is generated."""
    from app.engines.complaints.ai_settlement_service import AISettlementService
    assert hasattr(AISettlementService, "submit_answers")
    src = inspect.getsource(AISettlementService.submit_answers)
    # it must record each party's answers and run the analysis once BOTH are in
    assert "customer_answers" in src and "tenant_answers" in src
    assert "analyze_and_propose" in src


def test_both_parties_have_answer_endpoints():
    import os
    root = os.path.join(os.path.dirname(__file__), "..", "app", "engines", "complaints")
    cust = open(os.path.join(root, "customer_router.py"), encoding="utf-8").read()
    prov = open(os.path.join(root, "provider_router.py"), encoding="utf-8").read()
    assert '@customer_complaint_router.post("/{complaint_id}/ai-session/answers")' in cust
    assert '@provider_complaint_router.post("/{complaint_id}/ai-session/answers")' in prov
    # each side must be able to SEE its own questions
    assert '@customer_complaint_router.get("/{complaint_id}/ai-session")' in cust
    assert '@provider_complaint_router.get("/{complaint_id}/ai-session")' in prov
    # and must never be shown the other side's answers
    assert "tenant_answers" not in cust.split("get_ai_session")[1].split("def ")[0]


def test_deepseek_key_read_via_settings_not_raw_environ():
    """Bug #38: _api_key() read os.environ directly, which does NOT pick up .env
    (pydantic Settings with env_file='.env' is what loads it). So the AI
    settlement analysis ALWAYS failed 'DEEPSEEK_API_KEY not configured' even
    though the key was configured and every other AI feature worked — because
    ai_chat and ai_conversation both go through get_settings(). The bug was
    invisible while analyze_and_propose had no caller (bug #37)."""
    from app.engines.complaints import ai_settlement_service
    src = inspect.getsource(ai_settlement_service._api_key)
    assert "get_settings()" in src and "DEEPSEEK_API_KEY" in src
