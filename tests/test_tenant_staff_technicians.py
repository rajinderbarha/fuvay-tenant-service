"""Staff & Technicians onboarding step — readiness/coverage/validation tests."""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
ROUTER = os.path.join(BASE, "app/engines/provider_portal/router.py")
READINESS = os.path.join(BASE, "app/engines/home_service_assignment/team_readiness_service.py")
ASSIGN_SVC = os.path.join(BASE, "app/engines/home_service_assignment/service.py")


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class TestRouterHardening:
    def test_create_login_no_longer_returns_null_credentials_stub(self):
        c = _read(ROUTER)
        assert 'return ok({"member_id": str(member_id), "credentials": None}' not in c
        assert "activation_token" in c

    def test_activation_token_never_returned_outside_debug(self):
        c = _read(ROUTER)
        assert "activation_token\": token_plain if settings.DEBUG else None" in c

    def test_activation_endpoint_is_public_no_auth_dependency(self):
        c = _read(ROUTER)
        idx = c.index('@router.post("/team-members/activate")')
        block = c[idx:idx + 600]
        assert "UserContext = Depends(get_current_user)" not in block
        assert "UserContext = Depends(require_tenant_owner_mutation)" not in block

    def test_activation_error_is_generic_no_enumeration(self):
        c = _read(ROUTER)
        assert "This activation link is invalid or has expired." in c

    def test_category_id_is_server_derived_not_client_trusted(self):
        c = _read(ROUTER)
        assert "cat_id = str(await resolve_team_category_id(db, tid))" in c
        idx = c.index("async def create_team_member")
        block = c[idx:idx + 2500]
        assert 'payload.get("category_id")' not in block

    def test_member_type_validated_against_canonical_set(self):
        c = _read(ROUTER)
        assert 'VALID_MEMBER_TYPES = {"technician", "staff", "manager"}' in c
        assert "tenant_manager" not in c
        assert "tenant_finance" not in c
        assert "dispatcher" not in c

    def test_offering_ids_validated_against_real_tenant_services(self):
        c = _read(ROUTER)
        assert "async def _validate_offering_ids" in c
        assert "INVALID_SERVICE_ASSIGNMENT" in c

    def test_jsonb_assignments_are_serialized_on_update(self):
        """Editing service assignments must use the same JSON encoding as create.

        asyncpg's JSONB codec accepts an encoded JSON string for a raw text()
        statement; handing it a Python list caused the live Team modal to
        return HTTP 500 for every assignment edit.
        """
        c = _read(ROUTER)
        idx = c.index("async def update_team_member")
        block = c[idx:idx + 6500]
        assert 'json_array_fields = {' in block
        for field in (
            "supported_offering_ids",
            "supported_type_ids",
            "supported_brand_ids",
            "service_area_ids",
        ):
            assert f'"{field}"' in block
        assert "params[field] = json.dumps" in block

    def test_cross_tenant_account_takeover_rejected(self):
        c = _read(ROUTER)
        assert "CROSS_TENANT_ACCOUNT_EXISTS" in c

    def test_deactivate_revokes_sessions_db_and_redis(self):
        c = _read(ROUTER)
        idx = c.index("async def deactivate_team_member")
        block = c[idx:idx + 2500]
        assert "revoked_at" in block
        assert "serviceos:session:revoked:" in block

    def test_no_out_of_scope_fields_collected(self):
        c = _read(ROUTER)
        idx = c.index("async def create_team_member")
        block = c[idx:idx + 3000]
        for forbidden in ("salary", "bank_account", "security_deposit", "city_tier"):
            assert forbidden not in block

    def test_service_coverage_is_exposed_before_dynamic_member_route(self):
        c = _read(ROUTER)
        static_idx = c.index('@router.get("/team-members/service-coverage")')
        dynamic_idx = c.index('@router.get("/team-members/{member_id}")')
        assert static_idx < dynamic_idx
        block = c[static_idx:dynamic_idx]
        assert "compute_service_coverage" in block
        assert 'ok({"coverage": coverage}' in block


class TestReadinessCalculation:
    def test_readiness_states_are_specific_not_generic_active_flag(self):
        c = _read(READINESS)
        assert 'f"needs_{headline}"' in c
        for reason in ("identity", "role", "service_assignment", "availability"):
            assert f'"{reason}"' in c
        assert '"access_disabled"' in c
        assert '"ready"' in c

    def test_offering_ids_revalidated_at_readiness_time_not_trusted(self):
        c = _read(READINESS)
        assert "_validate_offering_ids" in c
        assert "is_enabled=true" in c

    def test_availability_check_scoped_to_staff_member(self):
        c = _read(READINESS)
        assert "scope_type='staff_member'" in c

    def test_coverage_only_counts_technician_required_offerings(self):
        c = _read(READINESS)
        assert "technician_required" in c
        assert "if not o.technician_required" in c

    def test_coverage_counts_ready_not_merely_assigned_technicians(self):
        c = _read(READINESS)
        idx = c.index("async def compute_service_coverage")
        block = c[idx:]
        assert 'readiness["status"] == "ready"' in block


class TestEligibilityGateHardening:
    def test_skill_match_check_added(self):
        c = _read(ASSIGN_SVC)
        assert "no_matching_service_skill" in c

    def test_availability_check_added(self):
        c = _read(ASSIGN_SVC)
        assert "no_availability_configured" in c

    def test_technician_required_flag_looked_up_not_assumed(self):
        c = _read(ASSIGN_SVC)
        assert "_job_requires_technician" in c
        # technician_required belongs to the versioned ServiceJobWorkflow,
        # not JobTypeDefinition; jobs snapshot that workflow id at creation.
        assert "ServiceJobWorkflow.technician_required" in c

    def test_offering_match_uses_real_job_offering_id(self):
        c = _read(ASSIGN_SVC)
        assert "_tenant_service_id_for_job" in c
        assert "TenantService.master_service_id == job.offering_id" in c
        assert "TenantService.job_type_id == job.job_type_id" in c
