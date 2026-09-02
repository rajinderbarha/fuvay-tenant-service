"""MODULE-L5-02 bug #41 — customer & provider could not SEE the AI session.

The AI settlement asks BOTH the customer and the provider clarifying questions
(bugs #37/#38), and answering them is what runs the analysis. But neither app had
any UI for it: the questions were asked into the void as far as the two people
who had to answer were concerned. Added an AI-settlement section to both complaint
detail pages, backed by the per-side ai-session endpoints.
"""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
CUST_API  = os.path.join(ROOT, "mobile", "customer-app", "src", "api", "supportRequests", "supportRequestsApi.ts")
CUST_PAGE = os.path.join(ROOT, "mobile", "customer-app", "src", "screens", "support", "SupportRequestDetailsScreen.tsx")
PROV_PAGE = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)", "provider", "complaints", "[complaint_id]", "page.tsx")


def test_customer_app_has_no_retired_ai_session_client_or_ui():
    api = open(CUST_API, encoding="utf-8").read()
    assert "getMySupportRequestAiSession" not in api
    assert "/ai-session" not in api
    page = open(CUST_PAGE, encoding="utf-8").read()
    assert "Details needed for resolution" not in page
    assert "customer_questions" not in page and "handleSubmitAiAnswers" not in page


def test_provider_app_has_no_retired_ai_session_tab():
    page = open(PROV_PAGE, encoding="utf-8").read()
    assert "/ai-session" not in page
    assert "tenant_questions" not in page
    assert '"ai"' not in page
