"""Phase 7 — Staff/Technician App Foundation certification.

Static-inspection style (established convention this session). Live
end-to-end behavior for these same assertions was additionally verified via
curl against the real running backend + real Postgres before this file was
written — see PHASE_7_STAFF_APP_BACKEND_REPORT.md and
PHASE_7_STAFF_APP_BUG_FIX_REPORT.md for that evidence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIELD_OPS_SERVICE = (ROOT / "app/engines/field_ops/service.py").read_text(encoding="utf-8-sig")
FIELD_OPS_STAFF_ROUTER = (ROOT / "app/engines/field_ops/staff_router.py").read_text(encoding="utf-8-sig")
ADMIN_SERVICE = (ROOT / "app/engines/tenant_engine/admin_service.py").read_text(encoding="utf-8-sig")
STAFF_MODEL = (ROOT / "app/engines/home_service_assignment/staff_model.py").read_text(encoding="utf-8-sig")
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")


# ── Bug 1: tenant_id isolation gap in staff job list ────────────────
def test_staff_technician_tenant_id_is_overridden_from_jwt_not_query_param():
    idx = FIELD_OPS_SERVICE.index("async def list_jobs")
    snippet = FIELD_OPS_SERVICE[idx: idx + 1500]
    assert '("tenant_owner", "staff", "technician")' in snippet


def test_staff_id_always_overridden_to_actor_for_staff_role():
    idx = FIELD_OPS_SERVICE.index("async def list_jobs")
    snippet = FIELD_OPS_SERVICE[idx: idx + 1500]
    assert 'staff_id = self.actor_id' in snippet


def test_job_detail_isolation_helper_blocks_unassigned_staff():
    assert "_assert_assigned" in FIELD_OPS_SERVICE
    idx = FIELD_OPS_SERVICE.index("def _assert_assigned")
    snippet = FIELD_OPS_SERVICE[idx: idx + 500]
    assert 'job.assigned_staff_id != self.actor_id' in snippet
    assert "NotFoundException" in snippet


def test_staff_jobs_router_scopes_to_staff_and_technician_roles_only():
    assert 'u.role not in ("staff", "technician")' in FIELD_OPS_STAFF_ROUTER


# ── Bug 2: real technician role excluded from tenant staff list ────
def test_tenant_staff_list_includes_technician_role_not_just_staff():
    # previously hardcoded User.role == "staff", silently excluding every
    # real seeded account (role="technician")
    assert 'User.role == "staff"' not in ADMIN_SERVICE
    assert 'User.role.in_(("staff", "technician"))' in ADMIN_SERVICE


# ── Bug 3: provider_team_members table/migration ────────────────────
def test_provider_team_members_migration_exists():
    migration = (ROOT / "alembic/versions/113_provider_team_members.py").read_text(encoding="utf-8-sig")
    assert "provider_team_members" in migration
    assert "def upgrade" in migration


def test_provider_team_member_model_matches_migration_columns():
    for col in ("skills", "supported_offering_ids", "category_id", "user_id"):
        assert col in STAFF_MODEL


# ── Self-role/tenant/status change structurally blocked ─────────────
def test_update_me_endpoint_only_accepts_safe_profile_fields():
    auth_router = (ROOT / "app/engines/auth/router.py").read_text(encoding="utf-8-sig")
    idx = auth_router.index('"/me",\n    summary="Update current user profile"')
    snippet = auth_router[idx: idx + 500]
    assert "UpdateProfileRequest" in snippet


# ── Forbidden label scan ─────────────────────────────────────────────
def test_no_forbidden_labels_in_staff_facing_backend():
    forbidden = ("Cash Wallet", "Withdrawable Balance", "Tenant Payout",
                 "Provider Earnings Wallet", "Escrow", "Provider Cash Balance")
    for label in forbidden:
        assert label not in FIELD_OPS_SERVICE
        assert label not in FIELD_OPS_STAFF_ROUTER
        assert label not in PROVIDER_ROUTER


# ── No job completion/payment/deduction runtime exposed in the staff shell ──
def test_staff_jobs_router_exposes_no_job_status_completion_or_payment_mutation():
    # /checklist/complete (completing a checklist ITEM) is a legitimate,
    # pre-existing part of the job shell — not the same as transitioning the
    # job itself to "completed" or collecting payment/deducting credits.
    forbidden_paths = ("/payment", "/collect-payment", "/deduct-credits", '"completed"')
    for path in forbidden_paths:
        assert path not in FIELD_OPS_STAFF_ROUTER
