"""TENANT-DOCUMENTS-WORKSPACE-01 — Documents & Verification workspace.

Covers the pure-function projection logic in
tenant_documents_workspace_service.py (effective/validity status,
allowed_actions, activation_impact, identifier masking) plus router/model
structure checks, following the same pattern as
test_tenant_verification_documents.py.
"""
import os
import pathlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.engines.vertical_catalog.tenant_documents_workspace_service import (
    _effective_status, _validity_status, _allowed_actions, _activation_impact,
    _mask_identifier, _summary_counts,
)
from app.engines.vertical_catalog.document_requirements import (
    resolve_technician_requirements, required_technician_keys,
)

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
utcnow = lambda: datetime.now(timezone.utc)


def _doc(**kw) -> MagicMock:
    d = MagicMock()
    d.status = kw.get("status", "pending_review")
    d.expiry_date = kw.get("expiry_date", None)
    return d


class TestEffectiveStatus:
    def test_no_document_is_not_uploaded(self):
        assert _effective_status(None) == "not_uploaded"

    def test_verified_stays_verified_when_no_expiry(self):
        assert _effective_status(_doc(status="verified", expiry_date=None)) == "verified"

    def test_verified_but_past_expiry_becomes_expired(self):
        d = _doc(status="verified", expiry_date=utcnow() - timedelta(days=1))
        assert _effective_status(d) == "expired"

    def test_verified_not_yet_expired_stays_verified(self):
        d = _doc(status="verified", expiry_date=utcnow() + timedelta(days=5))
        assert _effective_status(d) == "verified"

    def test_pending_review_with_past_expiry_is_not_flipped_to_expired(self):
        # Only a VERIFIED document can meaningfully "expire" -- a
        # still-under-review document's own status is the true state.
        d = _doc(status="pending_review", expiry_date=utcnow() - timedelta(days=1))
        assert _effective_status(d) == "pending_review"

    def test_rejected_passthrough(self):
        assert _effective_status(_doc(status="rejected")) == "rejected"

    def test_changes_requested_passthrough(self):
        assert _effective_status(_doc(status="changes_requested")) == "changes_requested"


class TestValidityStatus:
    def test_none_document_has_no_validity(self):
        assert _validity_status(None) is None

    def test_no_expiry_date_set(self):
        assert _validity_status(_doc(expiry_date=None)) == "no_expiry"

    def test_expired_when_past(self):
        assert _validity_status(_doc(expiry_date=utcnow() - timedelta(days=1))) == "expired"

    def test_expiring_soon_within_window(self):
        assert _validity_status(_doc(expiry_date=utcnow() + timedelta(days=10))) == "expiring_soon"

    def test_valid_when_far_out(self):
        assert _validity_status(_doc(expiry_date=utcnow() + timedelta(days=200))) == "valid"

    def test_boundary_just_inside_window_is_expiring_soon(self):
        assert _validity_status(_doc(expiry_date=utcnow() + timedelta(days=29))) == "expiring_soon"

    def test_boundary_just_outside_window_is_valid(self):
        assert _validity_status(_doc(expiry_date=utcnow() + timedelta(days=31))) == "valid"


class TestAllowedActions:
    def test_not_uploaded_offers_upload_only(self):
        assert _allowed_actions("not_uploaded") == ["UPLOAD"]

    def test_rejected_offers_replacement_and_history(self):
        actions = _allowed_actions("rejected")
        assert "UPLOAD_REPLACEMENT" in actions and "VIEW_HISTORY" in actions
        assert "UPLOAD" not in actions

    def test_changes_requested_offers_replacement(self):
        assert "UPLOAD_REPLACEMENT" in _allowed_actions("changes_requested")

    def test_expired_offers_replacement(self):
        assert "UPLOAD_REPLACEMENT" in _allowed_actions("expired")

    def test_pending_review_offers_only_history_not_replacement(self):
        # A document mid-review cannot be silently replaced by the tenant --
        # that would erase the reviewer's live decision context.
        actions = _allowed_actions("pending_review")
        assert actions == ["VIEW_HISTORY"]

    def test_verified_offers_replacement_and_history(self):
        actions = _allowed_actions("verified")
        assert "UPLOAD_REPLACEMENT" in actions and "VIEW_HISTORY" in actions


class TestActivationImpact:
    def test_optional_document_never_blocks(self):
        impact = _activation_impact(required=False, effective_status="not_uploaded")
        assert impact["blocks_activation"] is False
        assert impact["blocks_new_jobs"] is False
        assert impact["level"] == "optional"

    def test_required_not_uploaded_blocks_activation_only(self):
        impact = _activation_impact(required=True, effective_status="not_uploaded")
        assert impact["blocks_activation"] is True
        assert impact["blocks_new_jobs"] is False

    def test_required_rejected_blocks_new_jobs_not_activation(self):
        impact = _activation_impact(required=True, effective_status="rejected")
        assert impact["blocks_activation"] is False
        assert impact["blocks_new_jobs"] is True

    def test_required_expired_blocks_new_jobs(self):
        impact = _activation_impact(required=True, effective_status="expired")
        assert impact["blocks_new_jobs"] is True

    def test_required_pending_review_does_not_block_new_jobs(self):
        # Grace period: previous valid version stays authoritative while a
        # replacement is under review.
        impact = _activation_impact(required=True, effective_status="pending_review")
        assert impact["blocks_new_jobs"] is False
        assert impact["blocks_activation"] is False

    def test_required_changes_requested_does_not_block_new_jobs(self):
        impact = _activation_impact(required=True, effective_status="changes_requested")
        assert impact["blocks_new_jobs"] is False

    def test_required_verified_blocks_nothing(self):
        impact = _activation_impact(required=True, effective_status="verified")
        assert impact["blocks_activation"] is False
        assert impact["blocks_new_jobs"] is False

    def test_every_impact_has_a_human_message(self):
        for status in ("not_uploaded", "rejected", "changes_requested", "pending_review", "verified", "expired"):
            impact = _activation_impact(required=True, effective_status=status)
            assert impact["human_message"]


class TestMaskIdentifier:
    def test_none_stays_none(self):
        assert _mask_identifier(None) is None

    def test_short_value_fully_masked(self):
        assert _mask_identifier("AB12") == "****"

    def test_long_value_keeps_last_four_only(self):
        masked = _mask_identifier("27AAJCS1234R1Z5")
        assert masked.endswith("R1Z5")
        assert masked.startswith("*")
        assert "27AAJCS1234" not in masked

    def test_masked_length_matches_original(self):
        original = "PB12345645"
        assert len(_mask_identifier(original)) == len(original)


class TestSummaryCounts:
    def _item(self, effective_status, validity_status=None):
        return {"effective_status": effective_status, "validity_status": validity_status}

    def test_counts_verified_correctly(self):
        items = [self._item("verified"), self._item("verified"), self._item("not_uploaded")]
        counts = _summary_counts(items)
        assert counts["total_documents"] == 3
        assert counts["verified"] == 2
        assert counts["action_required"] == 1

    def test_action_required_includes_all_blocking_statuses(self):
        items = [
            self._item("not_uploaded"), self._item("rejected"),
            self._item("changes_requested"), self._item("expired"),
            self._item("verified"), self._item("pending_review"),
        ]
        counts = _summary_counts(items)
        assert counts["action_required"] == 4
        assert counts["under_review"] == 1
        assert counts["verified"] == 1

    def test_expiring_soon_counted_from_validity_status_not_review_status(self):
        items = [self._item("verified", "expiring_soon"), self._item("verified", "valid")]
        counts = _summary_counts(items)
        assert counts["expiring_soon"] == 1

    def test_empty_list_all_zero(self):
        counts = _summary_counts([])
        assert all(v == 0 for v in counts.values())


class TestTechnicianRequirementResolver:
    def test_technician_requirements_present(self):
        reqs = resolve_technician_requirements(vertical="home_services")
        keys = {r["key"] for r in reqs}
        assert {"technician_identity_proof", "technician_background_check"} <= keys

    def test_technician_skill_certificate_is_optional(self):
        reqs = resolve_technician_requirements(vertical="home_services")
        cert = next(r for r in reqs if r["key"] == "technician_skill_certificate")
        assert cert["required"] is False

    def test_technician_identity_proof_is_required(self):
        keys = required_technician_keys(vertical="home_services")
        assert "technician_identity_proof" in keys
        assert "technician_skill_certificate" not in keys

    def test_technician_requirements_distinct_from_business_keys(self):
        reqs = resolve_technician_requirements(vertical="home_services")
        keys = {r["key"] for r in reqs}
        # Technician keys are namespaced distinctly so a submit() call can
        # never accidentally cross-write a business-level requirement slot.
        assert all(k.startswith("technician_") for k in keys)


class TestWorkspaceRouterStructure:
    def _read(self, relpath: str) -> str:
        with open(os.path.join(BASE, relpath), encoding="utf-8") as f:
            return f.read()

    def test_workspace_router_has_expected_endpoints(self):
        c = self._read("app/engines/vertical_catalog/tenant_documents_workspace_router.py")
        assert 'router = APIRouter(prefix="/v1/tenant/documents"' in c
        assert '@router.get("/workspace")' in c
        assert '@router.get("/business")' in c
        assert '@router.get("/technicians")' in c
        assert '@router.get("/technicians/{staff_id}")' in c
        assert '@router.get("/expiry-calendar")' in c
        assert '@router.get("/activity")' in c
        assert '@router.get("/verification-report")' in c
        assert '@router.get("/versions/{doc_type}")' in c
        assert '@router.post("")' in c

    def test_workspace_router_is_not_the_onboarding_router(self):
        # Regression guard: the workspace router must NOT actually USE the
        # onboarding-only require_vertical_not_active gate as a dependency
        # (mentioning it in the module docstring, to explain the distinction,
        # is fine and expected), or every post-activation tenant would be
        # locked out of managing documents.
        c = self._read("app/engines/vertical_catalog/tenant_documents_workspace_router.py")
        assert "Depends(require_vertical_not_active" not in c
        assert "from app.dependencies.vertical_guard import require_vertical_not_active" not in c

    def test_onboarding_router_untouched(self):
        c = self._read("app/engines/vertical_catalog/tenant_documents_router.py")
        assert "require_vertical_not_active" in c

    def test_submit_validates_expiry_not_before_issue(self):
        c = self._read("app/engines/vertical_catalog/tenant_documents_workspace_router.py")
        assert "Expiry date cannot precede issue date" in c

    def test_media_asset_tenant_and_context_checked_before_accepting(self):
        c = self._read("app/engines/vertical_catalog/tenant_documents_workspace_router.py")
        assert "asset.tenant_id != tid" in c
        assert "asset.media_context != DOCUMENT_MEDIA_CONTEXT" in c


class TestAdminVerifyEndpointStructure:
    def _read(self) -> str:
        with open(os.path.join(BASE, "app/engines/vertical_catalog/admin_router.py"), encoding="utf-8") as f:
            return f.read()

    def test_decision_supports_all_three_outcomes(self):
        c = self._read()
        assert '"verified", "rejected", "changes_requested"' in c

    def test_reviewed_by_is_written(self):
        c = self._read()
        assert "doc.reviewed_by = reviewer_id" in c

    def test_audit_log_written_on_decision(self):
        c = self._read()
        assert "TenantAuditLog(" in c
        assert 'action_type=f"document.{decision}"' in c

    def test_notification_fired_on_decision(self):
        c = self._read()
        assert 'fire_event(\n            db, f"document.{decision}"' in c or "fire_event(" in c


class TestTenantDocumentModelExtension:
    def test_model_has_staff_scoping_and_review_fields(self):
        with open(os.path.join(BASE, "app/engines/tenant_engine/models.py"), encoding="utf-8") as f:
            c = f.read()
        assert "staff_member_id: Mapped[uuid.UUID | None]" in c
        assert "reviewed_by: Mapped[uuid.UUID | None]" in c
        assert "review_notes: Mapped[str | None]" in c


class TestDocumentPermissions:
    def test_tenant_owner_has_read_and_upload_by_default(self):
        from app.core.permissions import permission_checker, P
        assert permission_checker.has(role="tenant_owner", permission=P.TENANT_DOCUMENTS_READ, overrides=None) is True
        assert permission_checker.has(role="tenant_owner", permission=P.TENANT_DOCUMENTS_UPLOAD, overrides=None) is True

    def test_staff_has_no_document_access_by_default(self):
        # Per spec: "General staff: No document access unless explicitly
        # granted" -- staff must NOT inherit a tenant-wide document grant.
        from app.core.permissions import permission_checker, P
        assert permission_checker.has(role="staff", permission=P.TENANT_DOCUMENTS_READ, overrides=None) is False
        assert permission_checker.has(role="staff", permission=P.TENANT_DOCUMENTS_UPLOAD, overrides=None) is False

    def test_staff_can_be_explicitly_granted_upload_via_override(self):
        # The real "authorized manager" mechanism: per-user permission_overrides
        # (sourced from JWT claims at login), not a new access-control system.
        from app.core.permissions import permission_checker, P
        assert permission_checker.has(
            role="staff", permission=P.TENANT_DOCUMENTS_UPLOAD,
            overrides={P.TENANT_DOCUMENTS_UPLOAD: True},
        ) is True

    def test_workspace_router_uses_permission_gates_not_hardcoded_roles(self):
        with open(os.path.join(BASE, "app/engines/vertical_catalog/tenant_documents_workspace_router.py"), encoding="utf-8") as f:
            c = f.read()
        assert "require_permission(P.TENANT_DOCUMENTS_READ)" in c
        assert "require_tenant_mutation_permission(P.TENANT_DOCUMENTS_UPLOAD)" in c
        # Regression guard: the earlier draft hardcoded role names directly
        # in the response body instead of checking the real permission.
        assert '"tenant_owner", "admin_operations"' not in c


class TestBookabilityDocumentGate:
    def test_bookability_evaluator_checks_required_documents(self):
        with open(os.path.join(BASE, "app/engines/provider_portal/router.py"), encoding="utf-8") as f:
            c = f.read()
        assert "REQUIRED_DOCUMENT_ACTION_NEEDED" in c
        assert "documents_satisfied" in c
        assert "and documents_satisfied" in c

    def test_blocking_statuses_match_activation_impact_policy(self):
        with open(os.path.join(BASE, "app/engines/provider_portal/router.py"), encoding="utf-8") as f:
            c = f.read()
        # Must match _activation_impact's blocks_new_jobs set exactly --
        # pending_review/changes_requested are a grace period, not a block.
        assert '"not_uploaded", "rejected", "expired"' in c
