"""MODULE-L5-02 bug #41 — customer & provider could not SEE the AI session.

The AI settlement asks BOTH the customer and the provider clarifying questions
(bugs #37/#38), and answering them is what runs the analysis. But neither app had
any UI for it: the questions were asked into the void as far as the two people
who had to answer were concerned. Added an AI-settlement section to both complaint
detail pages, backed by the per-side ai-session endpoints.
"""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
CUST_API  = os.path.join(ROOT, "frontend", "customer-app", "lib", "api", "customer-complaints.ts")
CUST_PAGE = os.path.join(ROOT, "frontend", "customer-app", "app", "customer", "complaints", "[complaintId]", "page.tsx")
PROV_PAGE = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)", "provider", "complaints", "[complaint_id]", "page.tsx")


def test_customer_app_has_ai_session_client_and_ui():
    api = open(CUST_API, encoding="utf-8").read()
    assert "getAISession" in api and "submitAIAnswers" in api
    assert "/ai-session/answers" in api
    page = open(CUST_PAGE, encoding="utf-8").read()
    assert "AI settlement" in page
    assert "customer_questions" in page and "submitAIAnswers" in page
    # never renders the other side's answers
    assert "tenant_answers" not in page


def test_provider_app_has_ai_session_tab():
    page = open(PROV_PAGE, encoding="utf-8").read()
    assert "/ai-session" in page and "/ai-session/answers" in page
    assert "tenant_questions" in page
    assert '"ai"' in page  # the tab
    # never renders the customer's answers
    assert "customer_answers" not in page
