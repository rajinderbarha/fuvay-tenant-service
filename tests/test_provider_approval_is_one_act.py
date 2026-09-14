"""Approving a provider approves them.

The console reported "pending document approval" against a provider an admin
had just approved: `verify_tenant` set the tenant approved but never touched
the documents, and the approval gate demanded every required document already
be individually `verified`. Two states for one decision, and no way to
reconcile them from the approval screen.

Approving IS the verification of the business, so a document merely awaiting
review no longer blocks it -- approval marks those verified in the same act.

Two cases still block, because approval cannot honestly resolve them:

  not_uploaded                    there is nothing to verify;
  rejected / changes_requested    an admin already made a deliberate negative
                                  decision, and approving must not silently
                                  overturn it.
"""
from __future__ import annotations

import inspect


class TestAwaitingReviewNoLongerBlocks:
    def test_pending_review_is_not_a_blocker(self):
        from app.engines.provider_portal import admin_router
        src = inspect.getsource(admin_router._build_admin_review_context)
        # The old rule blocked on anything that was not already verified.
        assert 'item["status"] != "verified"' not in src
        assert "REQUIRED_DOCUMENT_NOT_VERIFIED" not in src

    def test_a_missing_document_still_blocks(self):
        from app.engines.provider_portal import admin_router
        src = inspect.getsource(admin_router._build_admin_review_context)
        assert "REQUIRED_DOCUMENT_MISSING" in src
        assert '"not_uploaded"' in src

    def test_a_rejected_document_still_blocks(self):
        from app.engines.provider_portal import admin_router
        src = inspect.getsource(admin_router._build_admin_review_context)
        # Approving must not silently overturn a deliberate rejection.
        assert "REQUIRED_DOCUMENT_REJECTED" in src
        assert '"changes_requested"' in src


class TestApprovalVerifiesTheDocuments:
    def test_approval_marks_awaiting_documents_verified(self):
        from app.engines.provider_portal import admin_router
        src = inspect.getsource(admin_router)
        idx = src.index("documents_verified_on_approval")
        window = src[max(0, idx - 900):idx]
        assert "UPDATE tenant_documents SET status = 'verified'" in window
        assert "status = 'pending_review'" in window

    def test_it_records_who_verified_and_when(self):
        """Deleting the evidence later is only defensible if the verification
        record itself survives."""
        from app.engines.provider_portal import admin_router
        src = inspect.getsource(admin_router)
        idx = src.index("documents_verified_on_approval")
        window = src[max(0, idx - 900):idx]
        assert "verified_at = now()" in window
        assert "verified_by" in window

    def test_only_current_documents_are_touched(self):
        from app.engines.provider_portal import admin_router
        src = inspect.getsource(admin_router)
        idx = src.index("documents_verified_on_approval")
        window = src[max(0, idx - 900):idx]
        # A superseded version must keep the status it had.
        assert "is_current = true" in window

    def test_a_rejected_document_is_not_swept_up(self):
        from app.engines.provider_portal import admin_router
        src = inspect.getsource(admin_router)
        idx = src.index("documents_verified_on_approval")
        window = src[max(0, idx - 900):idx]
        # Only pending_review is promoted; rejection blocks approval anyway,
        # but the query must not be able to overturn one even so.
        assert "status = 'pending_review'" in window
        assert "'rejected'" not in window

    def test_the_count_is_reported_back(self):
        from app.engines.provider_portal import admin_router
        src = inspect.getsource(admin_router)
        assert 'result["documents_verified_on_approval"]' in src


class TestTheTenantSideStillReadsAsVerified:
    def test_bookability_is_unaffected_by_the_change(self):
        """The gate reads current documents and blocks on missing, rejected or
        expired. Approval promoting pending_review to verified can only help
        it, never weaken it."""
        # The evaluator lives in the tenant-facing router, not the admin one.
        from app.engines.provider_portal import router
        src = inspect.getsource(router._evaluate_provider_bookability)
        assert "REQUIRED_DOCUMENT_ACTION_NEEDED" in src

    def test_trust_quality_accepts_the_canonical_approved_status(self):
        from app.engines.trust_quality.service import _is_tenant_verified

        assert _is_tenant_verified("approved") is True
        assert _is_tenant_verified("verified") is True
        assert _is_tenant_verified("pending") is False

    def test_batch_recalculation_uses_the_same_verification_contract(self):
        from app.engines.trust_quality import recalculation

        src = inspect.getsource(recalculation.gather_metrics_bulk)
        assert '_is_tenant_verified(row["verification_status"])' in src


class TestSecureProviderDocumentPreview:
    def test_signed_remote_files_use_the_access_checked_delivery_resolver(self):
        from app.engines.media import admin_router

        src = inspect.getsource(admin_router.resolve_signed_media)
        delivery = inspect.getsource(admin_router._serve_admin_media)
        assert "_serve_admin_media(db, u, media_id, purpose)" in src
        assert "MediaAssetService(db=db, actor=actor)" in delivery
        assert "get_remote_url_for_serve(media_id)" in delivery
        assert "if asset.public_url" not in delivery
        assert "StreamingResponse" in delivery

    def test_production_preserves_local_fallback_files_across_rollouts(self):
        from pathlib import Path

        compose = Path("docker-compose.prod.yml").read_text(encoding="utf-8")
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
        assert compose.count("media_uploads:/app/uploads") == 2
        assert "media_uploads:" in compose
        assert "mkdir -p /app/uploads" in dockerfile


class TestTheAdminDocumentWorkflowIsGone:
    """Initial approval is one act; later replacement review is separate."""

    def test_the_per_document_verify_button_is_removed(self):
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(
            encoding="utf-8")
        assert 'reviewDocument(document.document_id!, "verified")' not in src

    def test_documents_stay_visible_and_openable(self):
        """An admin should see what they are approving."""
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(
            encoding="utf-8")
        assert "openAdminMediaPreview" in src
        assert "Verification documents" in src

    def test_request_changes_survives(self):
        """Without it, spotting one bad document would leave no option but
        rejecting the entire provider."""
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/providers/page.tsx").read_text(
            encoding="utf-8")
        assert "Request changes" in src

    def test_active_provider_replacements_can_be_reviewed(self):
        from app.engines.provider_portal import admin_router

        src = inspect.getsource(admin_router.review_provider_onboarding_document)
        assert "_require_submitted_review" not in src
        assert "terminated_at IS NULL" in src

        from pathlib import Path
        component = Path("frontend/super-admin/components/directory/ProviderDocuments.tsx").read_text(
            encoding="utf-8"
        )
        assert "Verify document" in component
        assert "replacement documents uploaded later" in component


class TestCreditThresholdsAreEditable:
    def test_the_floor_has_an_admin_surface(self):
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(
            encoding="utf-8")
        # It had none: the only card that ever edited this policy set the
        # starter-purchase fields, retired with the activation requirement.
        assert "CreditThresholdsSection" in src
        assert "Stop new bookings below" in src

    def test_the_warning_cannot_sit_below_the_floor(self):
        from app.engines.vertical_catalog.topup_plan_service import HomeServicesTopupPlanService
        errs = HomeServicesTopupPlanService()._validate(
            {"credit_booking_floor": 500, "credit_warning_threshold": 100})
        # A warning below the floor would only fire after bookings had stopped.
        assert any("at or above" in e for e in errs)
