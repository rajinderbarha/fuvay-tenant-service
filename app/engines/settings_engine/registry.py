"""CONFIGURATION-REGISTRY-REBUILD: code-defined setting definitions.

Mirrors the pattern already proven twice this session
(NotificationEventRegistry, then the notification policy engine) --
definitions are Python dataclasses registered at import time, never rows an
admin can invent. The admin-facing service/router validate every change
request against THIS registry; a key/scope/type not defined here is
rejected, not silently accepted.

Audit finding (Phase 1): of the ~70 pre-existing PlatformSetting rows, only
`booking_cancellation_window_hours` and `dispatch_score_weights` have a real
runtime reader (app/engines/booking/service.py, app/engines/dispatch/
service.py -- both via SettingsService.resolve()). Everything else was
admin-UI-only theater. This registry is honest about that split: entries
marked `has_real_consumer=True` are genuinely read by running code today;
the rest are registered (so a governed change-request workflow exists for
them) but have no consumer yet -- do not claim they affect runtime
behavior until a consumer is actually wired.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DATA_TYPES = {
    "boolean", "integer", "decimal", "string", "enum",
    "duration", "percentage", "timestamp", "structured",
}
SCOPES = {"global", "vertical", "environment"}  # tenant scope intentionally absent by default
SNAPSHOT_BEHAVIORS = {
    "new_records_only", "future_transitions", "all_active_records",
    "next_login_or_request", "restart_required",
}
SENSITIVITY = {"public", "internal", "secret"}
RISK_LEVELS = {"low", "medium", "high", "critical"}


@dataclass
class ConfigurationDefinition:
    key: str
    label: str
    description: str
    owner_module: str
    data_type: str
    allowed_scopes: list[str]
    default_value: Any
    risk_level: str = "low"
    admin_mutable: bool = True
    approval_required: bool = False
    restart_required: bool = False
    effective_date_supported: bool = True
    snapshot_behavior: str = "new_records_only"
    rollback_supported: bool = True
    deprecated: bool = False
    sensitivity: str = "internal"
    unit: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    enum_values: list[str] | None = None
    # Locked = a runtime safety invariant. No change request of any kind may
    # ever be created for it, regardless of role -- distinct from
    # admin_mutable=False, which just hides the edit action; a locked
    # setting's mutation attempt is a hard, tested rejection.
    locked: bool = False
    has_real_consumer: bool = False
    consumer_note: str = ""


_REGISTRY: dict[str, ConfigurationDefinition] = {}


def _reg(d: ConfigurationDefinition) -> None:
    assert d.data_type in DATA_TYPES, f"{d.key}: unknown data_type {d.data_type}"
    assert set(d.allowed_scopes) <= SCOPES, f"{d.key}: unknown scope in {d.allowed_scopes}"
    assert d.snapshot_behavior in SNAPSHOT_BEHAVIORS, f"{d.key}: unknown snapshot_behavior"
    assert d.sensitivity in SENSITIVITY, f"{d.key}: unknown sensitivity"
    assert d.risk_level in RISK_LEVELS, f"{d.key}: unknown risk_level"
    if d.locked:
        assert not d.admin_mutable, f"{d.key}: a locked setting cannot also be admin_mutable"
    _REGISTRY[d.key] = d


# ── Real, already-wired consumers (booking/dispatch) ─────────────────────────
_reg(ConfigurationDefinition(
    key="booking_cancellation_window_hours", label="Booking Cancellation Window",
    description="Hours before a scheduled booking after which a customer can no longer cancel without penalty.",
    owner_module="booking", data_type="duration", unit="hours",
    allowed_scopes=["global", "vertical"], default_value=24, minimum=1, maximum=168,
    risk_level="medium", approval_required=False, snapshot_behavior="new_records_only",
    has_real_consumer=True, consumer_note="app/engines/booking/service.py:837-844,1203-1207 via SettingsService.resolve()",
))

_reg(ConfigurationDefinition(
    key="dispatch_score_weights", label="Dispatch Score Weights",
    description="Weighting factors used by the dispatch engine's candidate scoring algorithm.",
    owner_module="dispatch", data_type="structured",
    allowed_scopes=["global"], default_value=None,
    risk_level="high", approval_required=True, snapshot_behavior="new_records_only",
    has_real_consumer=True, consumer_note="app/engines/dispatch/service.py:78-87 via SettingsService.resolve()",
))

# ── Registered but not yet wired to a real consumer (honest gap, not fabricated) ──
_reg(ConfigurationDefinition(
    key="quote_expiry_hours", label="Quote Expiry Period",
    description="Time a sent estimate remains valid before expiring.",
    owner_module="quote_checklist", data_type="duration", unit="hours",
    allowed_scopes=["global", "vertical"], default_value=72, minimum=1, maximum=168,
    risk_level="medium", approval_required=True, snapshot_behavior="new_records_only",
    has_real_consumer=False,
    consumer_note="Registered for governance; quote_checklist does not yet read this key at runtime (Phase 1 finding).",
))

_reg(ConfigurationDefinition(
    key="complaint_sla_warning_threshold_hours", label="Complaint SLA Warning Threshold",
    description="Hours before an SLA breach at which a complaint is flagged at_risk.",
    owner_module="complaints", data_type="duration", unit="hours",
    allowed_scopes=["global", "vertical"], default_value=4, minimum=1, maximum=72,
    risk_level="medium", approval_required=False, snapshot_behavior="future_transitions",
    has_real_consumer=False,
    consumer_note="Registered for governance; complaints/complaint_service.py uses its own hardcoded SLA constants today.",
))

_reg(ConfigurationDefinition(
    key="notification_retry_max_attempts", label="Notification Retry Attempts",
    description="Maximum delivery retry attempts for a failed notification outbox record.",
    owner_module="platform_notifications", data_type="integer",
    allowed_scopes=["global"], default_value=3, minimum=1, maximum=10,
    risk_level="low", approval_required=False, snapshot_behavior="all_active_records",
    has_real_consumer=False,
    consumer_note="Registered for governance; platform_notifications.constants.MAX_RETRY_COUNT is still a hardcoded constant.",
))

# ── Critical locked settings -- runtime safety invariants, never editable ───
_reg(ConfigurationDefinition(
    key="work_start_approval_enforcement", label="Work-Start Estimate Approval Enforcement",
    description="Whether a repair job requires customer estimate approval before work may start.",
    owner_module="execution", data_type="boolean",
    allowed_scopes=["global"], default_value=True,
    risk_level="critical", admin_mutable=False, locked=True, sensitivity="internal",
    snapshot_behavior="restart_required", rollback_supported=False,
    has_real_consumer=True, consumer_note="Enforced in code (job workflow gates), not settings-table-driven.",
))

_reg(ConfigurationDefinition(
    key="matching_policy_version", label="Provider Matching Policy Version",
    description="Deployed version of the provider-matching scoring policy.",
    owner_module="home_service_booking", data_type="string",
    allowed_scopes=["global"], default_value="HS_MATCHING_V3",
    risk_level="critical", admin_mutable=False, locked=True, sensitivity="internal",
    snapshot_behavior="restart_required", rollback_supported=False,
    has_real_consumer=True,
    consumer_note="app/engines/home_service_booking/matching_engine.py:71-79 -- hardcoded weight constants, code-deployed only.",
))

_reg(ConfigurationDefinition(
    key="payment_collection_enabled", label="Home Services Payment Collection",
    description="Whether Fuvay collects the Home Services job payment (vs. customer pays provider directly).",
    owner_module="platform_commerce", data_type="boolean",
    allowed_scopes=["global"], default_value=False,
    risk_level="critical", admin_mutable=False, locked=True, sensitivity="internal",
    snapshot_behavior="restart_required", rollback_supported=False,
    has_real_consumer=True,
    consumer_note="Actual behavior driven by the hardcoded 'customer_pays_provider_directly' constant across ~13 files "
                  "(Phase 1 finding); this locked flag documents the invariant, not a live business-logic switch.",
))


class ConfigurationRegistry:
    @classmethod
    def get(cls, key: str) -> ConfigurationDefinition | None:
        return _REGISTRY.get(key)

    @classmethod
    def all(cls) -> dict[str, ConfigurationDefinition]:
        return dict(_REGISTRY)

    @classmethod
    def all_keys(cls) -> list[str]:
        return list(_REGISTRY.keys())
