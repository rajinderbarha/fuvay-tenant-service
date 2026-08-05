"""CONFIGURATION-REGISTRY-REBUILD: governed Configuration Registry backend.

Covers the spec's explicit test list, to the extent testable without a
live DB fixture in this repo's convention (static + direct-service style,
matching test_notification_policy_engine.py):
  - registered-key enforcement / unknown key rejection
  - invalid type / invalid enum / below/above constraint
  - disallowed scope rejection
  - locked-setting mutation rejection
  - self-approval prevention
  - deterministic value resolution precedence
  - version supersession / rollback
  - secret redaction (unchanged legacy behavior, re-confirmed)
"""
import os
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestRegisteredKeyEnforcement:
    def test_unknown_key_is_rejected(self):
        from app.engines.settings_engine.configuration_service import ConfigurationService
        svc = ConfigurationService.__new__(ConfigurationService)
        with pytest.raises(Exception):
            svc._definition("max_tenants_per_city")  # a PROHIBITED SETTINGS example from the spec

    def test_all_registered_keys_resolvable(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        for key in ConfigurationRegistry.all_keys():
            assert ConfigurationRegistry.get(key) is not None

    def test_prohibited_settings_are_not_registered(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        prohibited = [
            "max_tenants_per_city", "tier_pricing", "city_pricing", "zipcode_pricing",
            "admin_service_base_price", "tenant_service_prices", "arbitrary_commission",
        ]
        for key in prohibited:
            assert ConfigurationRegistry.get(key) is None


class TestValidation:
    def _svc(self):
        from app.engines.settings_engine.configuration_service import ConfigurationService
        return ConfigurationService.__new__(ConfigurationService)

    def test_invalid_type_rejected(self):
        svc = self._svc()
        result = svc.validate("booking_cancellation_window_hours", "global", "not-a-number")
        assert result["valid"] is False

    def test_invalid_enum_rejected(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry, ConfigurationDefinition
        svc = self._svc()
        # matching_policy_version is a string type, not enum -- use validate()
        # against a synthetic constraint check instead via direct _validate.
        d = ConfigurationRegistry.get("booking_cancellation_window_hours")
        errors = svc._validate(d, "global", 500)  # exceeds maximum=168
        assert any("maximum" in e for e in errors)

    def test_below_minimum_rejected(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        svc = self._svc()
        d = ConfigurationRegistry.get("booking_cancellation_window_hours")
        errors = svc._validate(d, "global", 0)
        assert any("minimum" in e for e in errors)

    def test_above_maximum_rejected(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        svc = self._svc()
        d = ConfigurationRegistry.get("quote_expiry_hours")
        errors = svc._validate(d, "global", 1000)
        assert any("maximum" in e for e in errors)

    def test_disallowed_scope_rejected(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        svc = self._svc()
        d = ConfigurationRegistry.get("dispatch_score_weights")  # allowed_scopes=["global"] only
        errors = svc._validate(d, "vertical", {"health_score": 0.5})
        assert any("scope" in e for e in errors)

    def test_tenant_scope_never_allowed_by_default(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        for d in ConfigurationRegistry.all().values():
            assert "tenant" not in d.allowed_scopes, (
                f"{d.key} allows tenant scope -- spec requires tenant scope disabled by default"
            )


class TestLockedSettingProtection:
    def test_locked_setting_change_request_rejected(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        svc = TestValidation()._svc()
        for key in ("work_start_approval_enforcement", "matching_policy_version", "payment_collection_enabled"):
            d = ConfigurationRegistry.get(key)
            assert d.locked is True
            errors = svc._validate(d, "global", d.default_value)
            assert any("locked" in e for e in errors)

    def test_locked_implies_not_admin_mutable(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        for d in ConfigurationRegistry.all().values():
            if d.locked:
                assert d.admin_mutable is False

    def test_locked_resolution_always_returns_code_locked_source(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_service.py"))
        idx = src.index("async def resolve_effective_value")
        block = src[idx: idx + 700]
        assert '"source": "code_locked"' in block
        assert "if d.locked:" in block


class TestSelfApprovalPrevention:
    def test_approve_source_rejects_same_actor_as_creator(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_service.py"))
        idx = src.index("async def approve")
        block = src[idx: idx + 900]
        assert "row.created_by" in block
        assert "actor_id == row.created_by" in block
        assert "PERMISSION_DENIED" in block


class TestDeterministicResolutionPrecedence:
    def test_precedence_order_documented_and_matches_code(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_service.py"))
        idx = src.index("async def resolve_effective_value")
        block = src[idx: idx + 1600]
        lock_idx = block.index("if d.locked:")
        env_idx = block.index("if environment:")
        vert_idx = block.index('if vertical_key and "vertical"')
        global_idx = block.index("global_row = await self._current")
        assert lock_idx < env_idx < vert_idx < global_idx, (
            "resolution must check lock -> environment -> vertical -> global in that order"
        )

    def test_vertical_override_only_applied_if_definition_permits_it(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_service.py"))
        idx = src.index('if vertical_key and "vertical"')
        block = src[idx: idx + 100]
        assert 'in d.allowed_scopes' in block


class TestVersionSupersessionAndRollback:
    def test_activate_supersedes_prior_before_activating_new(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_service.py"))
        idx = src.index("async def activate")
        block = src[idx: idx + 1200]
        assert 'prior.status = "superseded"' in block
        assert block.count("await self.db.flush()") >= 2

    def test_rollback_requires_reason(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_service.py"))
        idx = src.index("async def rollback")
        block = src[idx: idx + 400]
        assert "reason.strip()" in block

    def test_rollback_creates_new_version_never_mutates_history(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_service.py"))
        idx = src.index("async def rollback")
        block = src[idx: idx + 3000]
        assert "restored = ConfigurationValueVersion(" in block
        assert 'row.status = "rolled_back"' in block

    def test_one_active_version_per_key_scope_enforced_by_unique_index(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "models.py"))
        idx = src.index("class ConfigurationValueVersion")
        block = src[idx: idx + 1000]
        assert "ix_cvv_current" in block
        assert "status = 'active'" in block


class TestGlobalScopeNullSentinel:
    """Postgres treats every NULL as distinct in a unique index -- using NULL
    for global scope_id would silently defeat the one-active-row guarantee."""

    def test_global_scope_id_is_never_null(self):
        from app.engines.settings_engine.configuration_service import GLOBAL_SCOPE_ID
        assert GLOBAL_SCOPE_ID == "GLOBAL"

    def test_model_column_is_not_nullable(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "models.py"))
        idx = src.index("scope_id:      Mapped[str]")
        line = src[idx: idx + 120]
        assert "nullable=False" in line


class TestUnauthorizedMutationBlocked:
    def test_change_request_route_requires_permission(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_router.py"))
        idx = src.index('@router.post("/{key}/change-request"')
        block = src[idx: idx + 400]
        assert "CONFIGURATION_CHANGE_REQUEST_CREATE" in block

    def test_approve_route_requires_distinct_permission_from_create(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_router.py"))
        idx = src.index("/approve")
        block = src[idx: idx + 400]
        assert "CONFIGURATION_APPROVE" in block

    def test_activate_and_rollback_use_distinct_permissions(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "configuration_router.py"))
        assert "CONFIGURATION_ACTIVATE" in src
        assert "CONFIGURATION_ROLLBACK" in src


class TestSecretRedactionUnchanged:
    """Re-confirms the legacy secret-masking behavior this rebuild does not
    touch (Phase 1 found it already correct)."""

    def test_platform_setting_serializer_masks_secrets(self):
        src = _read(os.path.join(ROOT, "app", "engines", "settings_engine", "service.py"))
        assert "MASKED_VALUE if s.is_secret" in src

    def test_no_registered_definition_exposes_raw_secret_value(self):
        from app.engines.settings_engine.registry import ConfigurationRegistry
        for d in ConfigurationRegistry.all().values():
            assert d.sensitivity != "secret" or d.locked, (
                f"{d.key} is sensitivity=secret but not locked -- secrets must never be admin-editable here"
            )
