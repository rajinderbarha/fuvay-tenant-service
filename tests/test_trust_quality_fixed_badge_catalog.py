"""Trust & Quality fixed badge catalog guard.

Badges are customer-facing trust assets. The admin may configure award rules,
but badge identities themselves are fixed: tenant/provider, staff and
technician each get exactly four possible badges.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.engines.trust_quality.service import (
    FIXED_BADGE_CATALOG,
    TrustQualityService,
    VALID_BADGE_TARGETS,
    VALID_HEALTH_TARGETS,
)
from app.exceptions import ServiceOSException

ROOT = Path(__file__).resolve().parents[1]
ADMIN_PAGE = ROOT / "frontend" / "super-admin" / "app" / "admin" / "trust-quality" / "page.tsx"
API_TS = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
EARNED_TAB = ADMIN_PAGE.parent / "EarnedTab.tsx"
ADMIN_ROUTER = ROOT / "app" / "engines" / "trust_quality" / "admin_router.py"
SERVICE = ROOT / "app" / "engines" / "trust_quality" / "service.py"


def test_fixed_catalog_has_four_badges_per_target():
    assert VALID_BADGE_TARGETS == {"tenant", "staff", "technician"}
    assert len(FIXED_BADGE_CATALOG) == 12

    by_target: dict[str, list[dict]] = {}
    for badge in FIXED_BADGE_CATALOG:
        by_target.setdefault(badge["target_type"], []).append(badge)

    assert set(by_target) == {"tenant", "staff", "technician"}
    for target, badges in by_target.items():
        assert len(badges) == 4, target
        assert sorted(b["level"] for b in badges) == [1, 2, 3, 4]
        assert len({b["badge_key"] for b in badges}) == 4
        assert len({b["icon"] for b in badges}) >= 3
        assert len({b["color"] for b in badges}) == 4


@pytest.mark.anyio
async def test_free_form_badge_creation_is_blocked():
    svc = TrustQualityService(db=None)  # create_badge_definition now rejects before DB access.
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_badge_definition({
            "badge_key": "custom_gold_star",
            "name": "Custom Gold Star",
            "target_type": "tenant",
        })
    assert "fixed" in str(exc.value).lower()


def test_admin_ui_no_longer_exposes_badge_creation_form():
    page = ADMIN_PAGE.read_text(encoding="utf-8")
    assert "BadgeDefinitionModal" not in page
    assert "createBadgeDefinition" not in page
    assert "+ New Badge<" not in page
    assert "Fixed customer trust catalog" in page


def test_admin_api_dropdown_targets_are_only_supported_badge_targets():
    src = API_TS.read_text(encoding="utf-8")
    assert 'badgeTargets: ["tenant", "staff", "technician"]' in src
    assert '"customer", "service", "category"' not in src[src.index("export const TQ_ENUMS"):src.index("export const trustQualityApi")]


def test_health_console_uses_only_operational_targets_and_no_duplicate_risk_tab():
    page = ADMIN_PAGE.read_text(encoding="utf-8")
    api = API_TS.read_text(encoding="utf-8")
    risk_tab = ADMIN_PAGE.parent / "RiskTab.tsx"

    assert VALID_HEALTH_TARGETS == {"tenant", "technician"}
    assert 'healthTargets: ["tenant", "technician"]' in api
    assert 'id: "risk"' not in page
    assert not risk_tab.exists()


def test_trust_quality_cleanup_migrations_protect_the_console_from_legacy_noise():
    cleanup = (ROOT / "alembic" / "versions" / "277_trust_quality_canonical_cleanup.py").read_text(encoding="utf-8")
    audit_cleanup = (ROOT / "alembic" / "versions" / "278_trust_quality_audit_noise_cleanup.py").read_text(encoding="utf-8")
    metric_alignment = (ROOT / "alembic" / "versions" / "279_trust_quality_live_metric_alignment.py").read_text(encoding="utf-8")

    assert "formula_key LIKE 'l5%'" in cleanup
    assert "uq_hf_one_active_target" in cleanup
    assert "badge_rule.simulated" in audit_cleanup
    assert "usage_credit_score" in metric_alignment
    assert "package_credit_score" in metric_alignment  # renamed from this legacy key


def test_earned_tab_defaults_to_a_searchable_paged_holder_directory():
    tab = EARNED_TAB.read_text(encoding="utf-8")
    api = API_TS.read_text(encoding="utf-8")
    router = ADMIN_ROUTER.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")

    assert "Current badge holders" in tab
    assert "listBadgeAssignments" in tab and "Pagination" in tab
    assert "Search holders" in tab and "Target type" in tab
    assert "Award source" in tab and "All badges" in tab
    assert "Manage" in tab and "Revoke" in tab
    assert "/v1/admin/trust-quality/badge-assignments" in api
    assert '@router.get("/badge-assignments")' in router
    assert "ba.status = 'active'" in service
    assert "ba.expires_at IS NULL OR ba.expires_at > now()" in service
    assert "holder_rank = 1" in service


def test_orphan_badge_assignments_have_a_cleanup_migration():
    cleanup = (ROOT / "alembic" / "versions" / "283_remove_orphan_badge_assignments.py").read_text(encoding="utf-8")
    assert "NOT EXISTS" in cleanup
    assert "FROM tenants" in cleanup
    assert "FROM users" in cleanup
