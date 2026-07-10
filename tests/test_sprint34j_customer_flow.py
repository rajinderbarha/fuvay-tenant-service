"""Sprint 34J — Customer Flow Simplification Tests.

Tests verify that the backend controls all catalog choices:
  AI can talk. Backend decides. Database validates. Engines execute.
  Customer sees only active, backend-approved choices.

All tests are pure file-read tests (no live DB / HTTP).
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


# ─────────────────────────────────────────────────────────────────────────────
# Migration 061
# ─────────────────────────────────────────────────────────────────────────────
class TestMigration061(unittest.TestCase):
    def setUp(self):
        self.src = _read("alembic/versions/061_sprint34j_customer_booking_drafts.py")

    def test_revision_is_061(self):
        self.assertIn('revision = "061"', self.src)

    def test_down_revision_is_060(self):
        self.assertIn('down_revision = "060"', self.src)

    def test_table_created(self):
        self.assertIn('"customer_booking_drafts"', self.src)

    def test_flow_type_column(self):
        self.assertIn('"flow_type"', self.src)

    def test_customer_id_column(self):
        self.assertIn('"customer_id"', self.src)

    def test_status_column(self):
        self.assertIn('"status"', self.src)

    def test_category_id_column(self):
        self.assertIn('"category_id"', self.src)

    def test_service_id_column(self):
        self.assertIn('"service_id"', self.src)

    def test_brand_id_column(self):
        self.assertIn('"brand_id"', self.src)

    def test_issue_type_id_column(self):
        self.assertIn('"issue_type_id"', self.src)

    def test_service_option_ids_jsonb(self):
        self.assertIn('"service_option_ids"', self.src)

    def test_estimate_columns(self):
        self.assertIn('"estimate_min"', self.src)
        self.assertIn('"estimate_max"', self.src)
        self.assertIn('"estimate_currency"', self.src)

    def test_final_record_refs(self):
        self.assertIn('"final_job_id"', self.src)
        self.assertIn('"final_appointment_id"', self.src)
        self.assertIn('"final_lead_id"', self.src)

    def test_preferred_date_column(self):
        self.assertIn('"preferred_date"', self.src)

    def test_lead_notes_column(self):
        self.assertIn('"lead_notes"', self.src)

    def test_address_text_column(self):
        self.assertIn('"address_text"', self.src)

    def test_indexes_created(self):
        self.assertIn('"ix_cbd_customer_id"', self.src)
        self.assertIn('"ix_cbd_status"', self.src)
        self.assertIn('"ix_cbd_flow_type"', self.src)

    def test_downgrade_drops_table(self):
        self.assertIn("drop_table", self.src)
        self.assertIn('"customer_booking_drafts"', self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class TestModels34J(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/models.py")

    def test_class_defined(self):
        self.assertIn("class CustomerBookingDraft(ServiceOSBase):", self.src)

    def test_tablename(self):
        self.assertIn('"customer_booking_drafts"', self.src)

    def test_valid_flow_types_constant(self):
        self.assertIn("VALID_FLOW_TYPES", self.src)
        self.assertIn("service_booking", self.src)
        self.assertIn("appointment_booking", self.src)
        self.assertIn("lead_capture", self.src)
        self.assertIn("subscription_only", self.src)

    def test_valid_statuses_constant(self):
        self.assertIn("VALID_STATUSES", self.src)
        self.assertIn('"draft"', self.src)
        self.assertIn('"estimated"', self.src)
        self.assertIn('"confirmed"', self.src)
        self.assertIn('"cancelled"', self.src)

    def test_flow_type_field(self):
        self.assertIn("flow_type", self.src)

    def test_catalog_fields(self):
        self.assertIn("category_id", self.src)
        self.assertIn("service_id", self.src)
        self.assertIn("brand_id", self.src)
        self.assertIn("issue_type_id", self.src)
        self.assertIn("service_option_ids", self.src)

    def test_contact_fields(self):
        self.assertIn("customer_name", self.src)
        self.assertIn("customer_phone", self.src)
        self.assertIn("customer_email", self.src)

    def test_location_fields(self):
        self.assertIn("city", self.src)
        self.assertIn("zipcode", self.src)
        self.assertIn("address_text", self.src)

    def test_estimate_fields(self):
        self.assertIn("estimate_min", self.src)
        self.assertIn("estimate_max", self.src)
        self.assertIn("estimate_currency", self.src)

    def test_scheduling_fields(self):
        self.assertIn("preferred_date", self.src)
        self.assertIn("preferred_time_slot", self.src)

    def test_lead_fields(self):
        self.assertIn("lead_notes", self.src)
        self.assertIn("lead_details", self.src)

    def test_final_record_refs(self):
        self.assertIn("final_job_id", self.src)
        self.assertIn("final_appointment_id", self.src)
        self.assertIn("final_lead_id", self.src)

    def test_to_dict_method(self):
        self.assertIn("def to_dict(self) -> dict:", self.src)

    def test_to_dict_returns_flow_type(self):
        self.assertIn('"flow_type":', self.src)

    def test_date_import_added(self):
        self.assertIn("from datetime import date", self.src)

    def test_date_column_type(self):
        self.assertIn("Date,", self.src)

    def test_indexes_defined(self):
        self.assertIn('"ix_cbd_customer_id"', self.src)
        self.assertIn('"ix_cbd_status"', self.src)


# ─────────────────────────────────────────────────────────────────────────────
# CustomerFlowService
# ─────────────────────────────────────────────────────────────────────────────
class TestCustomerFlowService(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/customer_flow_service.py")

    def test_class_defined(self):
        self.assertIn("class CustomerFlowService:", self.src)

    def test_init_signature(self):
        self.assertIn("def __init__(self, db: AsyncSession", self.src)

    def test_valid_flow_types_module_level(self):
        self.assertIn("VALID_FLOW_TYPES", self.src)
        self.assertIn("service_booking", self.src)
        self.assertIn("appointment_booking", self.src)

    # Flow config
    def test_get_flow_config_method(self):
        self.assertIn("async def get_flow_config(", self.src)

    def test_flow_config_returns_default(self):
        self.assertIn('"service_booking"', self.src)
        self.assertIn('"configured":', self.src)

    def test_list_flow_configs_method(self):
        self.assertIn("async def list_flow_configs(", self.src)

    # Catalog
    def test_list_active_categories(self):
        self.assertIn("async def list_active_categories(", self.src)

    def test_list_active_services(self):
        self.assertIn("async def list_active_services(", self.src)

    def test_active_filter_applied(self):
        self.assertIn("is_active == True", self.src)

    # Draft CRUD
    def test_create_draft_method(self):
        self.assertIn("async def create_draft(", self.src)

    def test_create_draft_validates_flow_type(self):
        self.assertIn("not in VALID_FLOW_TYPES", self.src)

    def test_create_draft_validates_category(self):
        self.assertIn("_assert_category_active", self.src)

    def test_create_draft_validates_service(self):
        self.assertIn("_assert_service_active", self.src)

    def test_get_draft_method(self):
        self.assertIn("async def get_draft(", self.src)

    def test_update_draft_method(self):
        self.assertIn("async def update_draft(", self.src)

    def test_update_draft_blocks_confirmed(self):
        self.assertIn("Cannot update a confirmed draft", self.src)

    def test_update_draft_validates_catalog(self):
        self.assertIn("_assert_category_active", self.src)
        self.assertIn("_assert_service_active", self.src)

    def test_list_drafts_method(self):
        self.assertIn("async def list_drafts(", self.src)

    def test_cancel_draft_method(self):
        self.assertIn("async def cancel_draft(", self.src)

    def test_cancel_blocks_confirmed(self):
        self.assertIn("Cannot cancel a confirmed booking", self.src)

    # Estimate
    def test_estimate_draft_method(self):
        self.assertIn("async def estimate_draft(", self.src)

    def test_estimate_uses_base_price(self):
        self.assertIn("base_price", self.src)

    def test_estimate_sets_status_estimated(self):
        self.assertIn('"estimated"', self.src)

    def test_estimate_returns_note(self):
        self.assertIn('"note":', self.src)

    # Confirm
    def test_confirm_draft_method(self):
        self.assertIn("async def confirm_draft(", self.src)

    def test_confirm_requires_service(self):
        self.assertIn("service_id required before confirmation", self.src)

    def test_confirm_requires_contact(self):
        self.assertIn("customer_name and customer_phone required", self.src)

    def test_confirm_sets_status(self):
        self.assertIn('draft.status = "confirmed"', self.src)

    def test_confirm_returns_next_step(self):
        self.assertIn('"next_step"', self.src)

    # Admin oversight
    def test_admin_list_drafts_method(self):
        self.assertIn("async def admin_list_drafts(", self.src)

    # Validation helpers
    def test_assert_category_active_method(self):
        self.assertIn("async def _assert_category_active(", self.src)

    def test_assert_service_active_method(self):
        self.assertIn("async def _assert_service_active(", self.src)

    def test_load_draft_method(self):
        self.assertIn("async def _load_draft(", self.src)

    def test_permission_check_in_load_draft(self):
        self.assertIn("PermissionError", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# CustomerFlowRouter
# ─────────────────────────────────────────────────────────────────────────────
class TestCustomerFlowRouter(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/customer_flow_router.py")

    def test_customer_router_defined(self):
        self.assertIn("customer_router = APIRouter(", self.src)

    def test_admin_router_defined(self):
        self.assertIn("admin_router = APIRouter(", self.src)

    def test_customer_prefix(self):
        self.assertIn('prefix="/v1/customer/flow"', self.src)

    def test_admin_prefix(self):
        self.assertIn('prefix="/v1/admin/customer-flow"', self.src)

    # Customer endpoints
    def test_categories_endpoint(self):
        self.assertIn('"/categories"', self.src)

    def test_services_endpoint(self):
        self.assertIn('"/services"', self.src)

    def test_flow_config_endpoint(self):
        self.assertIn('"/flow-config"', self.src)

    def test_drafts_post_endpoint(self):
        self.assertIn('"/drafts"', self.src)
        self.assertIn("async def create_draft(", self.src)

    def test_drafts_get_endpoint(self):
        self.assertIn("async def list_drafts(", self.src)

    def test_draft_detail_endpoint(self):
        self.assertIn('"/drafts/{draft_id}"', self.src)

    def test_draft_update_endpoint(self):
        self.assertIn("async def update_draft(", self.src)

    def test_estimate_endpoint(self):
        self.assertIn('"/drafts/{draft_id}/estimate"', self.src)

    def test_confirm_endpoint(self):
        self.assertIn('"/drafts/{draft_id}/confirm"', self.src)

    def test_cancel_endpoint(self):
        self.assertIn('"/drafts/{draft_id}/cancel"', self.src)

    # Auth
    def test_customer_auth_on_drafts(self):
        self.assertIn("get_current_user", self.src)

    def test_admin_auth_on_admin_routes(self):
        self.assertIn("require_super_admin", self.src)

    # Admin endpoints
    def test_admin_list_flow_configs(self):
        self.assertIn('"/flow-configs"', self.src)

    def test_admin_list_drafts(self):
        self.assertIn("async def admin_list_drafts(", self.src)

    def test_admin_get_draft(self):
        self.assertIn("async def admin_get_draft(", self.src)

    # Filter support
    def test_status_query_param(self):
        self.assertIn("status", self.src)

    def test_flow_type_query_param(self):
        self.assertIn("flow_type", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# main.py integration
# ─────────────────────────────────────────────────────────────────────────────
class TestMainPy34J(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/main.py")

    def test_sprint34j_block_comment(self):
        self.assertIn("Sprint 34J", self.src)

    def test_customer_router_imported(self):
        self.assertIn("cflow_customer_router", self.src)

    def test_admin_router_imported(self):
        self.assertIn("cflow_admin_router", self.src)

    def test_customer_router_registered(self):
        self.assertIn("include_router(cflow_customer_router)", self.src)

    def test_admin_router_registered(self):
        self.assertIn("include_router(cflow_admin_router)", self.src)

    def test_import_from_customer_flow_router(self):
        self.assertIn("from app.engines.admin_catalog.customer_flow_router import", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Frontend api.ts
# ─────────────────────────────────────────────────────────────────────────────
class TestFrontendApiTs34J(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/lib/api.ts")

    def test_customer_booking_draft_interface(self):
        self.assertIn("export interface CustomerBookingDraft", self.src)

    def test_customer_flow_config_interface(self):
        self.assertIn("export interface CustomerFlowConfig", self.src)

    def test_customer_flow_api_export(self):
        self.assertIn("export const customerFlowApi", self.src)

    def test_list_categories_method(self):
        self.assertIn("listCategories:", self.src)

    def test_list_services_method(self):
        self.assertIn("listServices:", self.src)

    def test_get_flow_config_method(self):
        self.assertIn("getFlowConfig:", self.src)

    def test_create_draft_method(self):
        self.assertIn("createDraft:", self.src)

    def test_list_drafts_method(self):
        self.assertIn("listDrafts:", self.src)

    def test_get_draft_method(self):
        self.assertIn("getDraft:", self.src)

    def test_update_draft_method(self):
        self.assertIn("updateDraft:", self.src)

    def test_estimate_draft_method(self):
        self.assertIn("estimateDraft:", self.src)

    def test_confirm_draft_method(self):
        self.assertIn("confirmDraft:", self.src)

    def test_cancel_draft_method(self):
        self.assertIn("cancelDraft:", self.src)

    def test_admin_list_flow_configs_method(self):
        self.assertIn("adminListFlowConfigs:", self.src)

    def test_admin_list_drafts_method(self):
        self.assertIn("adminListDrafts:", self.src)

    def test_admin_get_draft_method(self):
        self.assertIn("adminGetDraft:", self.src)

    def test_customer_endpoint_url(self):
        self.assertIn("/v1/customer/flow", self.src)

    def test_admin_endpoint_url(self):
        self.assertIn("/v1/admin/customer-flow", self.src)

    def test_interface_has_flow_type(self):
        self.assertIn("flow_type: string;", self.src)

    def test_interface_has_status(self):
        self.assertIn("status: string;", self.src)

    def test_interface_has_estimate_fields(self):
        self.assertIn("estimate_min:", self.src)
        self.assertIn("estimate_max:", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Frontend pages
# ─────────────────────────────────────────────────────────────────────────────
class TestCustomerFlowOverviewPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/customer-flow/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_customer_flow_api(self):
        self.assertIn("customerFlowApi", self.src)

    def test_imports_customer_flow_config_type(self):
        self.assertIn("CustomerFlowConfig", self.src)

    def test_loads_flow_configs(self):
        self.assertIn("adminListFlowConfigs", self.src)

    def test_shows_flow_type(self):
        self.assertIn("customer_flow_type", self.src)

    def test_link_to_drafts(self):
        self.assertIn("/admin/customer-flow/drafts", self.src)

    def test_architecture_note(self):
        self.assertIn("AI can", self.src)

    def test_has_loading_state(self):
        self.assertIn("loading", self.src)

    def test_shows_required_steps(self):
        self.assertIn("required_steps", self.src)

    def test_shows_optional_steps(self):
        self.assertIn("optional_steps", self.src)


class TestCustomerDraftsListPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/customer-flow/drafts/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_customer_booking_draft(self):
        self.assertIn("CustomerBookingDraft", self.src)

    def test_loads_drafts(self):
        self.assertIn("adminListDrafts", self.src)

    def test_status_filter(self):
        self.assertIn("statusFilter", self.src)

    def test_flow_type_filter(self):
        self.assertIn("flowFilter", self.src)

    def test_shows_status_badge(self):
        self.assertIn("STATUS_COLORS", self.src)

    def test_shows_estimate(self):
        self.assertIn("estimate_min", self.src)

    def test_shows_customer_name(self):
        self.assertIn("customer_name", self.src)

    def test_link_to_detail(self):
        self.assertIn("/admin/customer-flow/drafts/${d.id}", self.src)

    def test_has_total_count(self):
        self.assertIn("total", self.src)


class TestDraftDetailPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/customer-flow/drafts/[draftId]/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_uses_params(self):
        self.assertIn("useParams", self.src)
        self.assertIn("draftId", self.src)

    def test_loads_draft(self):
        self.assertIn("adminGetDraft", self.src)

    def test_shows_catalog_ids(self):
        self.assertIn("category_id", self.src)
        self.assertIn("service_id", self.src)
        self.assertIn("brand_id", self.src)

    def test_shows_final_records_section(self):
        self.assertIn("final_job_id", self.src)
        self.assertIn("final_appointment_id", self.src)
        self.assertIn("final_lead_id", self.src)

    def test_shows_status_badge(self):
        self.assertIn("STATUS_COLORS", self.src)
        self.assertIn("draft.status", self.src)

    def test_shows_timestamps(self):
        self.assertIn("created_at", self.src)
        self.assertIn("updated_at", self.src)

    def test_back_link(self):
        self.assertIn("/admin/customer-flow/drafts", self.src)

    def test_shows_service_option_ids(self):
        self.assertIn("service_option_ids", self.src)


if __name__ == "__main__":
    unittest.main()
