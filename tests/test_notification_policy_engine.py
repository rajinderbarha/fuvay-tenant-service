"""NOTIFICATION-CENTER-REBUILD: Event Policies backend (NotificationPolicy).

Static source-inspection style (consistent with test_p0_finance_enterprise.py's
convention in this repo). Covers:
  - mandatory-event channel requirement enforced at validate() time
  - publish requires a reason
  - draft->publish->superseded versioning never mutates a published row
  - summary numbers are computed from real tables, not hardcoded
  - safety indicators are read-only (never accepted from the draft payload)
"""
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
POLICY_SERVICE = os.path.join(ROOT, "app", "engines", "platform_notifications", "policy_service.py")
POLICY_ROUTER = os.path.join(ROOT, "app", "engines", "platform_notifications", "policy_router.py")
POLICY_MODELS = os.path.join(ROOT, "app", "engines", "platform_notifications", "policy_models.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestProviderReadinessBlocker:
    """A policy cannot require or make primary a channel with no working
    provider (spec: 'do not allow a policy to enable SMS/WhatsApp/email/push
    if no working provider exists'). Fallback channels are exempt."""

    def test_validate_rejects_required_channel_with_no_provider(self):
        from app.engines.platform_notifications.policy_service import NotificationPolicyService
        svc = NotificationPolicyService()
        result = svc.validate({"required_channels": ["sms"], "primary_channels": []}, "job.assigned")
        assert result["valid"] is False
        assert any("no working provider" in e for e in result["errors"])

    def test_validate_rejects_primary_channel_with_no_provider(self):
        from app.engines.platform_notifications.policy_service import NotificationPolicyService
        svc = NotificationPolicyService()
        result = svc.validate({"required_channels": ["in_app"], "primary_channels": ["email"]}, "job.assigned")
        assert result["valid"] is False

    def test_validate_allows_unready_channel_as_fallback_only(self):
        from app.engines.platform_notifications.policy_service import NotificationPolicyService
        svc = NotificationPolicyService()
        result = svc.validate({
            "required_channels": ["in_app"], "primary_channels": ["in_app"],
            "fallback_channels": ["email", "sms"],
        }, "job.assigned")
        assert result["valid"] is True

    def test_in_app_is_the_only_live_channel_today(self):
        from app.engines.platform_notifications.provider_status_service import _LIVE_CHANNELS
        assert _LIVE_CHANNELS == {"in_app"}


class TestChannelStatusHonesty:
    @pytest.mark.asyncio
    async def test_stub_channels_never_report_available(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.engines.platform_notifications.provider_status_service import ProviderStatusService

        db = MagicMock()
        aggregate_result = MagicMock()
        aggregate_result.all.return_value = []
        db.execute = AsyncMock(return_value=aggregate_result)
        items = await ProviderStatusService().list_channel_status(db)
        by_channel = {i["channel"]: i for i in items}
        assert by_channel["in_app"]["state"] == "Available"
        for ch in ("email", "sms", "whatsapp", "push"):
            assert by_channel[ch]["state"] != "Available"
            assert by_channel[ch]["credential_reference"] is None

    @pytest.mark.asyncio
    async def test_channel_status_uses_one_grouped_outbox_query(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.engines.platform_notifications.provider_status_service import ProviderStatusService

        db = MagicMock()
        aggregate_result = MagicMock()
        aggregate_result.all.return_value = []
        db.execute = AsyncMock(return_value=aggregate_result)
        await ProviderStatusService().list_channel_status(db)
        assert db.execute.await_count == 1

    def test_channel_status_never_returns_credentials(self):
        src = _read(os.path.join(ROOT, "app", "engines", "platform_notifications", "provider_status_service.py"))
        assert '"credential_reference": None' in src


class TestMandatoryEventValidation:
    def test_validate_rejects_mandatory_event_without_in_app_required(self):
        from app.engines.platform_notifications.policy_service import NotificationPolicyService
        svc = NotificationPolicyService()
        result = svc.validate({"required_channels": ["email"]}, "commission.failed")
        assert result["valid"] is False
        assert any("in_app" in e and "mandatory" in e for e in result["errors"])

    def test_validate_accepts_mandatory_event_with_in_app_required(self):
        from app.engines.platform_notifications.policy_service import NotificationPolicyService
        svc = NotificationPolicyService()
        result = svc.validate({"required_channels": ["in_app"]}, "commission.failed")
        assert result["valid"] is True

    def test_validate_rejects_unknown_event(self):
        from app.engines.platform_notifications.policy_service import NotificationPolicyService
        svc = NotificationPolicyService()
        result = svc.validate({}, "not.a.real.event")
        assert result["valid"] is False

    def test_validate_rejects_unknown_channel(self):
        from app.engines.platform_notifications.policy_service import NotificationPolicyService
        svc = NotificationPolicyService()
        result = svc.validate({"required_channels": ["carrier_pigeon"]}, "job.assigned")
        assert result["valid"] is False

    def test_validate_rejects_unknown_recipient_role(self):
        from app.engines.platform_notifications.policy_service import NotificationPolicyService
        svc = NotificationPolicyService()
        result = svc.validate({"recipient_rules": [{"recipient_role": "ceo"}]}, "job.assigned")
        assert result["valid"] is False


class TestPublishRequiresReason:
    def test_publish_source_requires_nonempty_reason(self):
        src = _read(POLICY_SERVICE)
        idx = src.index("async def publish")
        block = src[idx: idx + 400]
        assert "reason.strip()" in block
        assert "A reason is required" in block


class TestVersioningImmutability:
    def test_publish_supersedes_prior_before_activating_draft(self):
        src = _read(POLICY_SERVICE)
        idx = src.index("async def publish")
        block = src[idx: idx + 2000]
        assert 'prior.is_current = False' in block
        assert 'prior.status = "superseded"' in block
        # two flushes, not one -- avoids the transient unique-index violation
        assert block.count("await db.flush()") >= 2

    def test_save_draft_never_mutates_a_published_row(self):
        src = _read(POLICY_SERVICE)
        idx = src.index("async def save_draft")
        block = src[idx: idx + 1500]
        assert 'NotificationPolicy.status == "draft"' in block

    def test_unique_index_enforces_one_current_per_event_vertical(self):
        src = _read(POLICY_MODELS)
        assert "ix_notif_policy_current" in src
        assert "is_current = true" in src


class TestSummaryComputedFromRealTables:
    def test_summary_reads_notification_outbox_for_delivery_rate(self):
        src = _read(POLICY_ROUTER)
        assert "NotificationOutbox" in src
        assert "DELIVERY_FAILED" in src
        assert "DELIVERY_DELIVERED" in src

    def test_summary_registered_events_count_from_registry_not_hardcoded(self):
        src = _read(POLICY_ROUTER)
        assert "len(all_events)" in src
        assert '"registered_events": len(all_events)' in src

    def test_need_review_is_derived_not_hardcoded(self):
        src = _read(POLICY_ROUTER)
        assert '"need_review": len(all_events) - active_policies' in src


class TestSafetyIndicatorsReadOnly:
    """The Safety block (tenant isolation / vertical isolation / recipient
    validation / consent enforcement / template-variable validation / audit
    logging / idempotency key) must never be accepted from a draft payload --
    it reflects the pipeline's own structural guarantees, not admin config."""

    def test_draft_fields_do_not_include_safety_flags(self):
        from app.engines.platform_notifications.policy_service import _DRAFT_FIELDS
        for forbidden in ("tenant_isolation", "vertical_isolation", "recipient_validation",
                          "consent_enforcement", "template_variable_validation",
                          "audit_logging", "idempotency_key"):
            assert forbidden not in _DRAFT_FIELDS

    def test_detail_endpoint_returns_safety_as_static_computed_block(self):
        src = _read(POLICY_ROUTER)
        idx = src.index('"safety":')
        block = src[idx: idx + 400]
        assert '"tenant_isolation": True' in block
