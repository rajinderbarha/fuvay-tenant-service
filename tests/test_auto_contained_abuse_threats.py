"""Blocked abuse traffic must not remain an unresolved platform threat."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SECURITY = (ROOT / "app/core/security.py").read_text(encoding="utf-8")
DASHBOARD = (ROOT / "app/engines/dashboard_command_center/service.py").read_text(encoding="utf-8")
MIGRATION = (ROOT / "alembic/versions/364_auto_contain_blocked_abuse_events.py").read_text(encoding="utf-8")


def test_abuse_guard_records_successful_blocks_as_contained():
    start = CORE_SECURITY.index("async def record_abuse_event")
    block = CORE_SECURITY[start:CORE_SECURITY.index("async def enforce_otp_send_limits")]
    assert '"enforcement_result": "blocked"' in block
    assert '"containment": "automatic"' in block
    assert 'status="contained"' in block
    assert "auto_actioned=True" in block


def test_existing_auto_actioned_open_rows_are_safely_reclassified():
    assert 'down_revision = "363"' in MIGRATION
    assert "SET status = 'contained'" in MIGRATION
    assert "AND auto_actioned = true" in MIGRATION
    assert "AND source = 'abuse_guard'" in MIGRATION
    assert "was blocked by an abuse-control threshold" in MIGRATION


def test_platform_health_counts_only_unresolved_threat_lifecycle_states():
    predicate = "status IN ('open','investigating')"
    assert DASHBOARD.count(predicate) >= 2
    assert "suspicious_activity_logs WHERE status='open'" not in DASHBOARD
