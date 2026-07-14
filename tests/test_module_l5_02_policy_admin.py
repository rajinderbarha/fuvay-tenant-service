"""MODULE-L5-02 bug #39 + AI settlement rule admin surface."""
import os
import inspect


def test_policy_create_no_longer_requires_missing_policy_name():
    """Bug #39: policy_name is NOT NULL on the model but was absent from PolicyIn,
    so POST /v1/admin/complaint-policies ALWAYS 500'd with a NotNullViolation — a
    complaint policy (and therefore the AI settlement rule) could never be created
    at all. create_policy now defaults policy_name from the key."""
    from app.engines.complaints.complaint_service import ComplaintService
    src = inspect.getsource(ComplaintService.create_policy)
    assert "policy_name" in src and "setdefault" in src


def test_policy_schema_exposes_the_ai_rule_and_real_columns():
    from app.engines.complaints.admin_router import PolicyIn
    fields = set(PolicyIn.model_fields)
    for f in ("policy_name", "tenant_id", "category_id", "allow_rework",
              "ai_settlement_enabled", "ai_auto_start_on_provider_failure",
              "ai_settlement_max_pct", "ai_settlement_allowed_remedies",
              "settlement_payout_in_credits_only"):
        assert f in fields, f
    # `allow_rework_request` was a phantom (the column is allow_rework)
    assert "allow_rework_request" not in fields


def test_policy_to_dict_returns_the_ai_rule():
    """Without this the admin UI could set the rule but never read it back."""
    from app.engines.complaints.models import ComplaintPolicy
    src = inspect.getsource(ComplaintPolicy.to_dict)
    for f in ("ai_settlement_enabled", "ai_settlement_max_pct",
              "ai_settlement_allowed_remedies", "settlement_payout_in_credits_only"):
        assert f in src, f


def test_admin_policy_page_edits_the_rule():
    root = os.path.join(os.path.dirname(__file__), "..")
    page = open(os.path.join(root, "frontend", "super-admin", "app", "admin",
                             "complaint-policies", "page.tsx"), encoding="utf-8").read()
    assert "AI Settlement Rule" in page
    assert "ai_settlement_max_pct" in page
    assert "ai_settlement_allowed_remedies" in page
    assert "ai_auto_start_on_provider_failure" in page
    # the page must not offer a money remedy in the picker
    assert '"refund"' not in page.split("Remedies the AI may offer")[1].split("</div>")[0]
