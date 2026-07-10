"""P0 DPDP Compliance Command Center — static-inspection regression tests.

This sprint additively extends the existing compliance engine
(app/engines/compliance/{enterprise_service,admin_router}.py) with health
scoring, action-queue assign/escalate, an affected data map, legal holds,
and evidence packs (migration 107: dpdp_legal_holds, dpdp_evidence_packs,
dpdp_action_states). Existing request/export/consent/retention lifecycle
(migration 079) was already present and is exercised live in this sprint's
smoke test, not re-verified here.

Following this repo's established convention, these are Python
source-inspection tests via pytest.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICE = (ROOT / "app/engines/compliance/enterprise_service.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "app/engines/compliance/admin_router.py").read_text(encoding="utf-8")
PERMISSIONS = (ROOT / "app/core/permissions.py").read_text(encoding="utf-8")
MIGRATION = (ROOT / "alembic/versions/107_dpdp_compliance_command_center.py").read_text(encoding="utf-8")


def test_health_endpoint_and_score_exist():
    assert '@router.get("/dpdp/health"' in ROUTER
    assert "async def get_health" in SERVICE


def test_action_queue_endpoints_exist():
    assert '@router.get("/dpdp/action-queue"' in ROUTER
    assert '@router.post("/requests/{request_id}/assign"' in ROUTER
    assert '@router.post("/requests/{request_id}/escalate"' in ROUTER
    assert "async def get_action_queue" in SERVICE
    assert "async def assign_action" in SERVICE
    assert "async def escalate_action" in SERVICE


def test_data_map_endpoints_exist():
    assert '@router.get("/requests/{request_id}/data-map"' in ROUTER
    assert '@router.post("/requests/{request_id}/refresh-data-map"' in ROUTER
    assert "async def get_data_map" in SERVICE


def test_export_and_erasure_blocked_before_verification():
    assert 'req.verification_status not in ("verified", "waived_with_reason")' in SERVICE
    assert "Identity verification is required" in SERVICE


def test_erasure_blocked_by_active_legal_hold():
    assert "_active_legal_hold_for_subject" in SERVICE
    assert "blocks erasure for this subject" in SERVICE


def test_legal_hold_endpoints_exist():
    assert '@router.get("/dpdp/legal-holds"' in ROUTER
    assert '@router.post("/dpdp/legal-holds"' in ROUTER
    assert '@router.post("/dpdp/legal-holds/{hold_id}/release"' in ROUTER
    assert "async def apply_legal_hold" in SERVICE
    assert "async def release_legal_hold" in SERVICE


def test_legal_hold_requires_reason():
    assert '"Legal hold reason is required."' in SERVICE


def test_legal_hold_release_requires_reason():
    assert '"Release reason is required."' in SERVICE


def test_evidence_pack_endpoints_exist():
    assert '@router.post("/requests/{request_id}/generate-evidence-pack"' in ROUTER
    assert '@router.get("/dpdp/evidence-packs"' in ROUTER
    assert "async def generate_evidence_pack" in SERVICE
    assert "dpdp_evidence_packs" in SERVICE


def test_evidence_pack_includes_required_sections():
    assert '"request_summary"' in SERVICE
    assert '"data_map"' in SERVICE
    assert '"active_legal_hold"' in SERVICE
    assert '"exports"' in SERVICE
    assert '"audit_trail"' in SERVICE


def test_all_dpdp_permission_constants_exist():
    for perm in (
        "COMPLIANCE_DPDP_READ", "COMPLIANCE_DPDP_REQUESTS_CREATE",
        "COMPLIANCE_DPDP_REQUESTS_UPDATE", "COMPLIANCE_DPDP_REQUESTS_VERIFY",
        "COMPLIANCE_DPDP_REQUESTS_APPROVE", "COMPLIANCE_DPDP_REQUESTS_REJECT",
        "COMPLIANCE_DPDP_EXPORTS_GENERATE", "COMPLIANCE_DPDP_EXPORTS_DOWNLOAD",
        "COMPLIANCE_DPDP_ERASURE_VALIDATE", "COMPLIANCE_DPDP_ERASURE_RUN",
        "COMPLIANCE_DPDP_CONSENT_READ", "COMPLIANCE_DPDP_CONSENT_WITHDRAW",
        "COMPLIANCE_DPDP_RETENTION_MANAGE", "COMPLIANCE_DPDP_LEGAL_HOLDS_MANAGE",
        "COMPLIANCE_DPDP_EVIDENCE_GENERATE", "COMPLIANCE_DPDP_SETTINGS_MANAGE",
        "COMPLIANCE_DPDP_AUDIT_READ",
    ):
        assert perm in PERMISSIONS, f"missing permission constant {perm}"


def test_migration_107_creates_expected_tables():
    assert 'down_revision = "106"' in MIGRATION
    assert "dpdp_legal_holds" in MIGRATION
    assert "dpdp_evidence_packs" in MIGRATION
    assert "dpdp_action_states" in MIGRATION
    assert "hold_code" in MIGRATION and "unique=True" in MIGRATION


def test_all_new_mutations_are_audited():
    for op in ("request.assigned", "request.escalated", "legal_hold.applied",
               "legal_hold.released", "evidence_pack.generated"):
        assert op in SERVICE
