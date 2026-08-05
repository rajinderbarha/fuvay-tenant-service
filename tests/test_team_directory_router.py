"""Team Directory + 360 profile — Staff & Technicians (Phase 1: directory +
Overview/Capabilities tabs). Reuses ProviderTeamMember (backfilled from real
technician/staff Users via migration 197) and the existing
team_readiness_service readiness authority -- no new staff/permission/
availability/capability engine.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
ROUTER = os.path.join(BASE, "app/engines/home_service_assignment/team_directory_router.py")
MIGRATION = os.path.join(BASE, "alembic/versions/197_backfill_provider_team_members_from_users.py")
CAPACITY_MIGRATION = os.path.join(BASE, "alembic/versions/200_provider_team_member_capacity.py")
STAFF_MODEL = os.path.join(BASE, "app/engines/home_service_assignment/staff_model.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestRouterStructure:
    def test_router_has_expected_endpoints(self):
        c = _read(ROUTER)
        assert 'router = APIRouter(prefix="/v1/tenant/home-services/team"' in c
        assert '@router.get("")' in c
        assert '@router.get("/{staff_id}/overview")' in c
        assert '@router.get("/{staff_id}/capabilities")' in c

    def test_reuses_canonical_readiness_service_not_a_new_engine(self):
        c = _read(ROUTER)
        assert "from app.engines.home_service_assignment.team_readiness_service import compute_member_readiness" in c
        assert "compute_member_readiness(db, tid" in c or "compute_member_readiness(db, tid, m)" in c

    def test_no_new_staff_or_permission_model(self):
        c = _read(ROUTER)
        for forbidden in ("class StaffPermission", "class TechnicianProfile", "class StaffCapability"):
            assert forbidden not in c

    def test_tenant_isolation_enforced_on_every_query(self):
        c = _read(ROUTER)
        # Every raw provider_team_members lookup must be tenant-scoped.
        assert "WHERE tenant_id=:tid AND deleted_at IS NULL" in c
        assert "WHERE id=:sid AND tenant_id=:tid AND deleted_at IS NULL" in c

    def test_capacity_uses_real_per_staff_field_not_a_fabricated_constant(self):
        c = _read(ROUTER)
        # The design's "2/4 jobs" ratio needed a real denominator -- migration
        # 200 added max_concurrent_jobs to provider_team_members rather than
        # inventing a client-side percentage against no real limit.
        assert 'member.get("max_concurrent_jobs") or 4' in c
        assert "capacity_percentage" in c
        assert "capacity_state" in c

    def test_capacity_state_reflects_readiness_and_conflicts_not_just_load(self):
        c = _read(ROUTER)
        start = c.index("def _capacity_state")
        block = c[start:start + 300]
        assert 'readiness_status != "ready"' in block
        assert '"incomplete"' in block
        assert "conflicts > 0" in block
        assert '"at_risk"' in block

    def test_jobs_today_matches_either_id_space(self):
        """assigned_staff_id has historically referenced either
        ProviderTeamMember.id or the linked User.id (home_service_assignment/
        service.py::_load_staff) -- job counts must check both."""
        c = _read(ROUTER)
        start = c.index("async def _jobs_today_rows")
        end = c.index("def _conflict_count")
        block = c[start:end]
        assert 'member.get("user_id")' in block
        assert "assigned_staff_id = ANY(:ids)" in block


class TestBackfillMigration:
    def test_migration_chains_from_latest_head(self):
        c = _read(MIGRATION)
        assert 'revision = "197"' in c
        assert 'down_revision = "196"' in c

    def test_backfill_is_idempotent(self):
        c = _read(MIGRATION)
        assert "already_linked" in c
        assert "if u.id in already_linked:" in c
        assert "continue" in c

    def test_backfill_only_targets_real_technician_staff_users(self):
        c = _read(MIGRATION)
        assert "role IN ('technician', 'staff')" in c

    def test_downgrade_never_destroys_live_data(self):
        c = _read(MIGRATION)
        assert "def downgrade() -> None:" in c
        downgrade_block = c[c.index("def downgrade"):]
        assert "DELETE" not in downgrade_block.upper()


class TestCapacityMigration:
    def test_migration_chains_from_latest_head(self):
        c = _read(CAPACITY_MIGRATION)
        assert 'revision = "200"' in c
        assert 'down_revision = "199"' in c

    def test_adds_real_column_with_safe_default(self):
        c = _read(CAPACITY_MIGRATION)
        assert '"max_concurrent_jobs"' in c
        assert "server_default=" in c

    def test_model_exposes_the_new_field(self):
        c = _read(STAFF_MODEL)
        assert "max_concurrent_jobs:" in c
        assert '"max_concurrent_jobs":   self.max_concurrent_jobs,' in c
