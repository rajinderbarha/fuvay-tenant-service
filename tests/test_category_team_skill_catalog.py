"""Category team-skill catalog and provider selection contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "alembic/versions/294_category_skill_catalog.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "app/engines/admin_catalog/skill_catalog_router.py").read_text(encoding="utf-8")
PROVIDER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8")
TEAM_MODAL = (ROOT / "frontend/tenant-portal/components/onboarding/AddTeamMemberWizard.tsx").read_text(encoding="utf-8")
ADMIN_CATEGORY = (ROOT / "frontend/super-admin/app/admin/categories/[id]/page.tsx").read_text(encoding="utf-8")
TEAM_DIRECTORY = ROOT / "frontend/tenant-portal/app/(tenant)/provider/team-members/page.tsx"
TEAM_DETAIL = (ROOT / "frontend/tenant-portal/app/(tenant)/home-services/team/[[...staffId]]/page.tsx").read_text(encoding="utf-8")
TEAM_SETUP = (ROOT / "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/staff/page.tsx").read_text(encoding="utf-8")
ACTION_MENU = (ROOT / "frontend/packages/design-system/src/components/ActionMenu.tsx").read_text(encoding="utf-8")
DESIGN_THEME = (ROOT / "frontend/packages/design-system/src/theme.css").read_text(encoding="utf-8")
READINESS = (ROOT / "app/engines/home_service_assignment/team_readiness_service.py").read_text(encoding="utf-8")
TENANT_CATALOG = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8")


def test_normalized_catalog_and_assignment_tables_are_indexed():
    assert '"category_skills"' in MIGRATION
    assert '"provider_team_member_skills"' in MIGRATION
    assert "uq_category_skills_category_code" in MIGRATION
    assert "uq_ptms_member_skill" in MIGRATION
    assert "ix_ptms_tenant_skill_member" in MIGRATION


def test_catalog_is_category_scoped_and_has_retire_restore_lifecycle():
    assert '@admin_router.get("/{category_id}/skills")' in ROUTER
    assert '@admin_router.post("/{category_id}/skills/{skill_id}/retire")' in ROUTER
    assert '@admin_router.post("/{category_id}/skills/{skill_id}/restore")' in ROUTER
    assert "cs.category_id=:cid" in ROUTER
    assert "cs.status='active'" in ROUTER


def test_provider_catalog_returns_only_category_active_choices():
    assert '@provider_router.get("/team-skills")' in ROUTER
    assert "resolve_team_category_id" in ROUTER
    assert "skills are retired or do not belong to this business category" in ROUTER


def test_team_creation_no_longer_requires_legacy_tenant_category_column():
    assert "Complete the business workspace setup before adding team members" not in PROVIDER
    assert "resolve_team_category_id(db, tid)" in PROVIDER
    assert "TECHNICIAN_SERVICE_REQUIRED" in PROVIDER
    assert "TECHNICIAN_SKILL_REQUIRED" in PROVIDER


def test_staff_skills_are_validated_and_written_as_normalized_assignments():
    assert "validate_skill_ids" in PROVIDER
    assert "replace_member_skills" in PROVIDER
    assert 'payload.get("skill_ids")' in PROVIDER
    assert '"skills": json.dumps([skill["name"] for skill in selected_skills])' in PROVIDER


def test_provider_modal_has_no_free_text_skill_entry():
    assert "skillsText" not in TEAM_MODAL
    assert "Comma separated" not in TEAM_MODAL
    assert "providerTeamSkillsApi.list()" in TEAM_MODAL
    assert "selectedSkillIds" in TEAM_MODAL
    assert "skill_ids: isTechnician ? selectedSkillIds : []" in TEAM_MODAL


def test_all_onboarding_designations_are_controlled_dropdowns():
    assert "DESIGNATIONS_BY_MEMBER_TYPE" in TEAM_MODAL
    assert '<select value={designation}' in TEAM_MODAL
    assert 'return "Select a designation."' in TEAM_MODAL
    assert 'placeholder="Senior Technician"' not in TEAM_MODAL
    assert not TEAM_DIRECTORY.exists()
    assert "AddTeamMemberWizard" in TEAM_DETAIL


def test_designation_contract_is_enforced_server_side():
    assert "DESIGNATIONS_BY_MEMBER_TYPE" in PROVIDER
    assert "def _validate_designation" in PROVIDER
    assert "TEAM_DESIGNATION_REQUIRED" in PROVIDER
    assert "INVALID_TEAM_DESIGNATION" in PROVIDER


def test_admin_category_page_exposes_enterprise_skill_management():
    assert 'key: "skills", label: "Technician Skills"' in ADMIN_CATEGORY
    assert "function TechnicianSkillsTab" in ADMIN_CATEGORY
    assert "categoryRuntimeApi.createSkill" in ADMIN_CATEGORY
    assert "categoryRuntimeApi.retireSkill" in ADMIN_CATEGORY
    assert "categoryRuntimeApi.restoreSkill" in ADMIN_CATEGORY
    assert "<Pagination page={data?.page ?? page}" in ADMIN_CATEGORY
    assert 'pageCount={data?.pages}' in ADMIN_CATEGORY
    assert 'onPage={setPage} itemLabel="skills" alwaysShow' in ADMIN_CATEGORY


def test_email_can_be_added_later_before_login_invitation():
    assert "TEAM_MEMBER_EMAIL_REQUIRED" in PROVIDER
    assert "@tenant.local" not in PROVIDER
    assert "invite_resent" in PROVIDER
    assert "Add an email later" in TEAM_MODAL
    assert "Send app invitation" in TEAM_SETUP


def test_pending_invitation_is_not_mislabeled_as_disabled_access():
    assert '"status": "invitation_pending"' in READINESS
    assert "invitation_pending:" in TEAM_SETUP


def test_roster_action_menu_is_not_clipped_by_its_container():
    assert 'overflow: "visible", position: "relative"' in TEAM_SETUP
    assert "<ActionMenu" in TEAM_SETUP
    assert "createPortal(" in ACTION_MENU and "document.body" in ACTION_MENU
    assert "z-index: var(--z-popover, 10000)" in DESIGN_THEME


def test_team_service_selector_uses_canonical_names_and_groups_job_types():
    assert "MasterService.service_name" in TENANT_CATALOG
    assert 'JobTypeDefinition.label.label("job_type_label")' in TENANT_CATALOG
    assert '"service_name": service_name' in TENANT_CATALOG
    assert "byMasterService" in TEAM_MODAL
    assert "groupedServices.map" in TEAM_MODAL
    assert "offering.job_type_label || humanizeJobType" in TEAM_MODAL
    assert "s.tenant_display_name || s.job_type" not in TEAM_MODAL
