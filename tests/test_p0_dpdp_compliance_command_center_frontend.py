"""P0 DPDP Compliance Command Center — frontend static-inspection tests.

No JS test runner in this repo; Python source-inspection tests matching
tests/test_p0_admin_tenant_typescript_stabilization.py convention.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "frontend/super-admin/app/admin/compliance/page.tsx").read_text(encoding="utf-8")
API_TS = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")


def test_page_title_and_description_updated():
    assert "DPDP Compliance Command Center" in PAGE
    assert "erasure, portability, retention, exemptions, evidence" in PAGE


def test_kpi_cards_render():
    for label in ("Pending Erasure", "Pending Export", "Consent Withdrawal",
                  "Pending Verify", "SLA Breached", "SLA At Risk"):
        assert label in PAGE


def test_action_queue_tab_renders_with_meaningful_empty_state():
    assert '"action_queue"' in PAGE
    assert "No compliance actions pending." in PAGE
    assert "All DPDP requests are currently within SLA and no admin action is required." in PAGE


def test_new_request_wizard_or_form_opens():
    assert "showCreate" in PAGE
    assert "New Request" in PAGE


def test_request_detail_drawer_opens():
    assert "RequestDetailDrawer" in PAGE
    assert "setDetailReq" in PAGE


def test_verification_panel_renders():
    assert "Verify Identity" in PAGE
    assert "verification_status" in PAGE


def test_data_map_rendered_via_scanned_items():
    assert "Data Inventory Scan" in PAGE


def test_export_action_disabled_before_verification_enforced_server_side():
    # UI only shows Verify Identity as a prerequisite action; the actual gate
    # is enforced server-side (tested in test_p0_dpdp_compliance_command_center.py).
    assert 'request.verification_status === "pending"' in PAGE


def test_legal_hold_tab_renders():
    assert '"legal_holds"' in PAGE
    assert "Apply Legal Hold" in PAGE
    assert "No legal holds on record." in PAGE
    assert "Release" in PAGE


def test_consent_tab_renders():
    assert 'activeTab === "consent"' in PAGE


def test_retention_tab_renders():
    assert 'activeTab === "retention"' in PAGE


def test_audit_tab_renders():
    assert 'activeTab === "audit"' in PAGE


def test_health_panel_renders():
    assert "Compliance Health" in PAGE
    assert "Top Risks" in PAGE
    assert "Recommended" in PAGE


def test_evidence_pack_action_wired():
    assert "Generate Evidence Pack" in PAGE
    assert "onGenerateEvidence" in PAGE


def test_escalate_action_wired():
    assert "Escalate" in PAGE
    assert "onEscalate" in PAGE


def test_compliance_api_exposes_all_new_dpdp_methods():
    for method in (
        "getHealth", "getActionQueue", "assignRequest", "escalateRequest",
        "getDataMap", "refreshDataMap", "listLegalHolds", "applyLegalHold",
        "releaseLegalHold", "generateEvidencePack", "listEvidencePacks",
    ):
        assert f"{method}:" in API_TS, f"missing complianceApi.{method}"
