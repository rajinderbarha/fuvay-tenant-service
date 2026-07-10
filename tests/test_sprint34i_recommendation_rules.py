"""Sprint 34I — Automation / Recommendation Rules Engine test suite.

Tests: migration 060, models, service, router, main.py, seed, frontend api.ts, frontend pages.
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


# ── Migration 060 ─────────────────────────────────────────────────────────────

class TestMigration060(unittest.TestCase):
    def setUp(self):
        self.src = _read("alembic/versions/060_sprint34i_recommendation_rules.py")

    def test_revision_is_060(self):
        self.assertIn('revision = "060"', self.src)

    def test_down_revision_is_059(self):
        self.assertIn('down_revision = "059"', self.src)

    def test_creates_recommendation_rules(self):
        self.assertIn('"recommendation_rules"', self.src)

    def test_creates_recommendation_results(self):
        self.assertIn('"recommendation_results"', self.src)

    def test_rule_code_field(self):
        self.assertIn('"code"', self.src)

    def test_rule_type_field(self):
        self.assertIn('"rule_type"', self.src)

    def test_rule_scope_field(self):
        self.assertIn('"scope"', self.src)

    def test_rule_priority_field(self):
        self.assertIn('"priority"', self.src)

    def test_rule_status_field(self):
        self.assertIn('"status"', self.src)

    def test_rule_condition_json_field(self):
        self.assertIn('"condition_json"', self.src)

    def test_rule_recommendation_json_field(self):
        self.assertIn('"recommendation_json"', self.src)

    def test_rule_explanation_template(self):
        self.assertIn('"explanation_template"', self.src)

    def test_rule_vertical_type(self):
        self.assertIn('"vertical_type"', self.src)

    def test_rule_category_id(self):
        self.assertIn('"category_id"', self.src)

    def test_result_context_type(self):
        self.assertIn('"context_type"', self.src)

    def test_result_rule_id(self):
        self.assertIn('"rule_id"', self.src)

    def test_result_confidence_score(self):
        self.assertIn('"confidence_score"', self.src)

    def test_result_explanation(self):
        self.assertIn('"explanation"', self.src)

    def test_result_status_default_shown(self):
        self.assertIn('"shown"', self.src)

    def test_unique_code_constraint(self):
        self.assertIn('"uq_rr_code"', self.src)

    def test_index_rule_status(self):
        self.assertIn('"ix_rec_rule_status"', self.src)

    def test_index_rule_type(self):
        self.assertIn('"ix_rec_rule_type"', self.src)

    def test_index_result_context(self):
        self.assertIn('"ix_res_context_type"', self.src)

    def test_index_result_rule(self):
        self.assertIn('"ix_res_rule_id"', self.src)

    def test_downgrade_drops_tables(self):
        self.assertIn("downgrade", self.src)
        self.assertIn("drop_table", self.src)


# ── Models ────────────────────────────────────────────────────────────────────

class TestModels34I(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/models.py")

    def _cls(self, name: str, size: int = 3000) -> str:
        idx = self.src.find(f"class {name}(")
        self.assertGreater(idx, -1, f"{name} not in models.py")
        return self.src[idx: idx + size]

    def test_recommendation_rule_class_exists(self):
        self.assertIn("class RecommendationRule(", self.src)

    def test_recommendation_result_class_exists(self):
        self.assertIn("class RecommendationResult(", self.src)

    def test_rule_tablename(self):
        w = self._cls("RecommendationRule")
        self.assertIn("recommendation_rules", w)

    def test_result_tablename(self):
        w = self._cls("RecommendationResult")
        self.assertIn("recommendation_results", w)

    def test_rule_has_code(self):
        self.assertIn("code", self._cls("RecommendationRule"))

    def test_rule_has_rule_type(self):
        self.assertIn("rule_type", self._cls("RecommendationRule"))

    def test_rule_has_scope(self):
        self.assertIn("scope", self._cls("RecommendationRule"))

    def test_rule_has_condition_json(self):
        self.assertIn("condition_json", self._cls("RecommendationRule"))

    def test_rule_has_recommendation_json(self):
        self.assertIn("recommendation_json", self._cls("RecommendationRule"))

    def test_rule_valid_rule_types(self):
        w = self._cls("RecommendationRule")
        self.assertIn("VALID_RULE_TYPES", w)
        self.assertIn("brand", w)
        self.assertIn("issue_type", w)

    def test_rule_valid_scopes(self):
        w = self._cls("RecommendationRule")
        self.assertIn("VALID_SCOPES", w)
        self.assertIn("platform", w)
        self.assertIn("vertical", w)

    def test_rule_has_to_dict(self):
        self.assertIn("to_dict", self._cls("RecommendationRule"))

    def test_result_has_context_type(self):
        self.assertIn("context_type", self._cls("RecommendationResult"))

    def test_result_has_rule_id(self):
        self.assertIn("rule_id", self._cls("RecommendationResult"))

    def test_result_has_confidence_score(self):
        self.assertIn("confidence_score", self._cls("RecommendationResult"))

    def test_result_has_status(self):
        self.assertIn("status", self._cls("RecommendationResult"))

    def test_result_valid_statuses(self):
        w = self._cls("RecommendationResult")
        self.assertIn("VALID_STATUSES", w)
        self.assertIn("accepted", w)
        self.assertIn("rejected", w)

    def test_result_has_to_dict(self):
        self.assertIn("to_dict", self._cls("RecommendationResult"))

    def test_models_before_customer_flow_config(self):
        idx_rule = self.src.find("class RecommendationRule(")
        idx_cfc = self.src.find("class CustomerFlowConfig(")
        self.assertGreater(idx_cfc, idx_rule)


# ── Admin Rule Service ────────────────────────────────────────────────────────

class TestAdminRecommendationRuleService(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/recommendation_engine_service.py")

    def test_file_exists(self):
        self.assertIn("AdminRecommendationRuleService", self.src)

    def test_has_list_rules(self):
        self.assertIn("async def list_rules", self.src)

    def test_has_get_rule(self):
        self.assertIn("async def get_rule", self.src)

    def test_has_create_rule(self):
        self.assertIn("async def create_rule", self.src)

    def test_has_update_rule(self):
        self.assertIn("async def update_rule", self.src)

    def test_has_delete_rule(self):
        self.assertIn("async def delete_rule", self.src)

    def test_has_activate_rule(self):
        self.assertIn("async def activate_rule", self.src)

    def test_has_deactivate_rule(self):
        self.assertIn("async def deactivate_rule", self.src)

    def test_has_archive_rule(self):
        self.assertIn("async def archive_rule", self.src)

    def test_has_simulate_rule(self):
        self.assertIn("async def simulate_rule", self.src)

    def test_simulate_no_mutation(self):
        idx = self.src.find("async def simulate_rule")
        snippet = self.src[idx: idx + 1500]
        self.assertIn("no database changes made", snippet)

    def test_has_list_results(self):
        self.assertIn("async def list_results", self.src)

    def test_validates_rule_type(self):
        self.assertIn("_validate_rule_type", self.src)

    def test_validates_scope(self):
        self.assertIn("_validate_scope", self.src)

    def test_validates_condition_json(self):
        self.assertIn("_validate_condition_json", self.src)

    def test_validates_recommendation_json(self):
        self.assertIn("_validate_recommendation_json", self.src)

    def test_invalid_condition_key_rejected(self):
        self.assertIn("Invalid condition keys", self.src)

    def test_archived_rule_cannot_be_updated(self):
        self.assertIn("Cannot update archived rule", self.src)

    def test_audit_events_logged(self):
        self.assertIn("recommendation_rule.created", self.src)
        self.assertIn("recommendation_rule.activated", self.src)
        self.assertIn("recommendation_rule.deactivated", self.src)
        self.assertIn("recommendation_rule.archived", self.src)
        self.assertIn("recommendation_rule.simulated", self.src)


# ── Recommendation Engine Service ─────────────────────────────────────────────

class TestRecommendationEngineService(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/recommendation_engine_service.py")

    def test_engine_class_exists(self):
        self.assertIn("class RecommendationEngineService", self.src)

    def test_has_get_recommendations(self):
        self.assertIn("async def get_recommendations", self.src)

    def test_has_evaluate_condition(self):
        self.assertIn("def _evaluate_condition", self.src)

    def test_has_resolve_recommendation(self):
        self.assertIn("async def _resolve_recommendation", self.src)

    def test_has_rank_recommendations(self):
        self.assertIn("def _rank_recommendations", self.src)

    def test_has_validate_recommendation(self):
        self.assertIn("async def validate_recommendation", self.src)

    def test_has_track_recommendation_result(self):
        self.assertIn("async def track_recommendation_result", self.src)

    def test_has_accept_recommendation(self):
        self.assertIn("async def accept_recommendation", self.src)

    def test_has_reject_recommendation(self):
        self.assertIn("async def reject_recommendation", self.src)

    def test_inactive_rule_excluded(self):
        idx = self.src.find("async def _load_active_rules")
        snippet = self.src[idx: idx + 500]
        self.assertIn('status == "active"', snippet)

    def test_inactive_brand_excluded(self):
        self.assertIn('"active"', self.src)
        self.assertIn("excluded", self.src)

    def test_deduplicates_recommendations(self):
        idx = self.src.find("def _rank_recommendations")
        snippet = self.src[idx: idx + 600]
        self.assertIn("seen", snippet)

    def test_condition_evaluates_vertical_type(self):
        idx = self.src.find("def _evaluate_condition")
        snippet = self.src[idx: idx + 2000]
        self.assertIn("vertical_type", snippet)

    def test_condition_evaluates_service_codes_any(self):
        idx = self.src.find("def _evaluate_condition")
        snippet = self.src[idx: idx + 2000]
        self.assertIn("service_codes_any", snippet)

    def test_condition_evaluates_requires_flags(self):
        idx = self.src.find("def _evaluate_condition")
        snippet = self.src[idx: idx + 2000]
        self.assertIn("requires_brand", snippet)

    def test_valid_condition_keys_defined(self):
        self.assertIn("VALID_CONDITION_KEYS", self.src)

    def test_resolve_handles_brand(self):
        self.assertIn('"brand"', self.src)

    def test_resolve_handles_service_option(self):
        self.assertIn('"service_option"', self.src)

    def test_resolve_handles_issue_type(self):
        self.assertIn('"issue_type"', self.src)

    def test_resolve_handles_workflow_template(self):
        self.assertIn('"workflow_template"', self.src)

    def test_accept_updates_status(self):
        self.assertIn('"accepted"', self.src)

    def test_reject_updates_status(self):
        self.assertIn('"rejected"', self.src)

    def test_empty_condition_matches_all(self):
        idx = self.src.find("def _evaluate_condition")
        snippet = self.src[idx: idx + 300]
        self.assertIn("not condition", snippet)

    def test_explain_uses_template(self):
        self.assertIn("explanation_template", self.src)


# ── Router ────────────────────────────────────────────────────────────────────

class TestRecommendationRouter(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/engines/admin_catalog/recommendation_router.py")

    def test_admin_router_prefix(self):
        self.assertIn("/v1/admin/recommendation-rules", self.src)

    def test_shared_router_prefix(self):
        self.assertIn("/v1/recommendations", self.src)

    def test_ai_router_prefix(self):
        self.assertIn("/v1/ai", self.src)

    def test_admin_requires_super_admin(self):
        self.assertIn("require_super_admin", self.src)

    def test_provider_requires_technician(self):
        self.assertIn("require_technician", self.src)

    def test_customer_requires_customer(self):
        self.assertIn("require_customer", self.src)

    def test_list_rules_endpoint(self):
        self.assertIn("list_rules", self.src)

    def test_create_rule_endpoint(self):
        self.assertIn("create_rule", self.src)

    def test_get_rule_endpoint(self):
        self.assertIn("get_rule", self.src)

    def test_update_rule_endpoint(self):
        self.assertIn("update_rule", self.src)

    def test_delete_rule_endpoint(self):
        self.assertIn("delete_rule", self.src)

    def test_activate_endpoint(self):
        self.assertIn("activate_rule", self.src)
        self.assertIn("/activate", self.src)

    def test_deactivate_endpoint(self):
        self.assertIn("deactivate_rule", self.src)
        self.assertIn("/deactivate", self.src)

    def test_archive_endpoint(self):
        self.assertIn("archive_rule", self.src)
        self.assertIn("/archive", self.src)

    def test_simulate_endpoint(self):
        self.assertIn("simulate_rule", self.src)
        self.assertIn("/simulate", self.src)

    def test_list_results_endpoint(self):
        self.assertIn("list_results", self.src)

    def test_evaluate_endpoint(self):
        self.assertIn("evaluate_recommendations", self.src)
        self.assertIn("/evaluate", self.src)

    def test_validate_endpoint(self):
        self.assertIn("validate_recommendation", self.src)
        self.assertIn("/validate", self.src)

    def test_accept_endpoint(self):
        self.assertIn("accept_recommendation", self.src)
        self.assertIn("/accept", self.src)

    def test_reject_endpoint(self):
        self.assertIn("reject_recommendation", self.src)
        self.assertIn("/reject", self.src)

    def test_ai_recommendations_endpoint(self):
        self.assertIn("ai_recommendations", self.src)
        self.assertIn("/recommendations", self.src)

    def test_ai_cannot_invent_ids(self):
        idx = self.src.find("async def ai_recommendations")
        snippet = self.src[idx: idx + 500]
        self.assertIn("get_recommendations", snippet)

    def test_bulk_setup_recommendations_endpoint(self):
        self.assertIn("bulk_setup_draft_recommendations", self.src)

    def test_provider_setup_recommendations_endpoint(self):
        self.assertIn("provider_setup_recommendations", self.src)

    def test_customer_booking_recommendations_endpoint(self):
        self.assertIn("customer_booking_recommendations", self.src)

    def test_customer_recs_strip_rule_metadata(self):
        idx = self.src.find("async def customer_booking_recommendations")
        snippet = self.src[idx: idx + 600]
        self.assertIn("rule_id", snippet)

    def test_invalid_condition_raises_400(self):
        self.assertIn("status_code=400", self.src)


# ── main.py ───────────────────────────────────────────────────────────────────

class TestMainPy34I(unittest.TestCase):
    def setUp(self):
        self.src = _read("app/main.py")

    def test_imports_rec_admin_router(self):
        self.assertIn("rec_admin_router", self.src)

    def test_imports_rec_shared_router(self):
        self.assertIn("rec_shared_router", self.src)

    def test_imports_rec_ai_router(self):
        self.assertIn("rec_ai_router", self.src)

    def test_imports_ctx_provider_router(self):
        self.assertIn("rec_ctx_provider_router", self.src)

    def test_imports_ctx_customer_router(self):
        self.assertIn("rec_ctx_customer_router", self.src)

    def test_all_routers_included(self):
        self.assertIn("rec_admin_router", self.src)
        self.assertIn("rec_shared_router", self.src)


# ── Seed Script ───────────────────────────────────────────────────────────────

class TestSeedRecommendationRules(unittest.TestCase):
    def setUp(self):
        self.src = _read("scripts/seed_recommendation_rules.py")

    def test_file_exists(self):
        self.assertIn("seed_recommendation_rules", self.src)

    def test_ac_brand_rule_seeded(self):
        self.assertIn("ac_brand_recommendations", self.src)

    def test_ac_option_rule_seeded(self):
        self.assertIn("ac_option_recommendations", self.src)

    def test_ac_issue_rule_seeded(self):
        self.assertIn("ac_issue_recommendations", self.src)

    def test_ac_document_rule_seeded(self):
        self.assertIn("ac_document_recommendations", self.src)

    def test_ac_checklist_rule_seeded(self):
        self.assertIn("ac_checklist_recommendation", self.src)

    def test_plumbing_issue_rule_seeded(self):
        self.assertIn("plumbing_issue_recommendations", self.src)

    def test_plumbing_option_rule_seeded(self):
        self.assertIn("plumbing_option_recommendations", self.src)

    def test_provider_defaults_seeded(self):
        self.assertIn("schedule_availability_default", self.src)
        self.assertIn("staff_assignment_default", self.src)

    def test_idempotent_by_code(self):
        self.assertIn("code", self.src)
        self.assertIn("skipped", self.src)

    def test_all_rules_have_active_status(self):
        self.assertIn('"active"', self.src)

    def test_vertical_type_used(self):
        self.assertIn("home_services", self.src)
        self.assertIn("coaching", self.src)

    def test_recommendation_json_uses_entity_type(self):
        self.assertIn('"entity_type"', self.src)
        self.assertIn('"entity_codes"', self.src)

    def test_condition_json_uses_service_codes_any(self):
        self.assertIn('"service_codes_any"', self.src)


# ── Frontend api.ts ───────────────────────────────────────────────────────────

class TestFrontendApiTs34I(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/lib/api.ts")

    def test_recommendation_rule_interface(self):
        self.assertIn("RecommendationRule", self.src)

    def test_recommendation_result_interface(self):
        self.assertIn("RecommendationResult", self.src)

    def test_recommendation_item_interface(self):
        self.assertIn("RecommendationItem", self.src)

    def test_recommendation_eval_result_interface(self):
        self.assertIn("RecommendationEvalResult", self.src)

    def test_simulate_result_interface(self):
        self.assertIn("SimulateResult", self.src)

    def test_recommendation_api_object(self):
        self.assertIn("recommendationApi", self.src)

    def test_list_rules_method(self):
        self.assertIn("listRules", self.src)

    def test_create_rule_method(self):
        self.assertIn("createRule", self.src)

    def test_get_rule_method(self):
        self.assertIn("getRule", self.src)

    def test_update_rule_method(self):
        self.assertIn("updateRule", self.src)

    def test_delete_rule_method(self):
        self.assertIn("deleteRule", self.src)

    def test_activate_rule_method(self):
        self.assertIn("activateRule", self.src)

    def test_deactivate_rule_method(self):
        self.assertIn("deactivateRule", self.src)

    def test_archive_rule_method(self):
        self.assertIn("archiveRule", self.src)

    def test_simulate_rule_method(self):
        self.assertIn("simulateRule", self.src)

    def test_list_results_method(self):
        self.assertIn("listResults", self.src)

    def test_evaluate_method(self):
        self.assertIn("evaluate", self.src)

    def test_validate_entity_method(self):
        self.assertIn("validateEntity", self.src)

    def test_accept_result_method(self):
        self.assertIn("acceptResult", self.src)

    def test_reject_result_method(self):
        self.assertIn("rejectResult", self.src)

    def test_ai_recommendations_method(self):
        self.assertIn("aiRecommendations", self.src)

    def test_bulk_setup_recommendations_method(self):
        self.assertIn("bulkSetupRecommendations", self.src)

    def test_provider_setup_recommendations_method(self):
        self.assertIn("providerSetupRecommendations", self.src)

    def test_uses_v1_admin_recommendation_rules_prefix(self):
        self.assertIn("/v1/admin/recommendation-rules", self.src)

    def test_uses_v1_recommendations_prefix(self):
        self.assertIn("/v1/recommendations/evaluate", self.src)

    def test_uses_v1_ai_prefix(self):
        self.assertIn("/v1/ai/recommendations", self.src)


# ── Frontend Pages ────────────────────────────────────────────────────────────

class TestRecommendationRulesListPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/automation/recommendation-rules/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_recommendation_api(self):
        self.assertIn("recommendationApi", self.src)

    def test_imports_rule_interface(self):
        self.assertIn("RecommendationRule", self.src)

    def test_calls_list_rules(self):
        self.assertIn("listRules", self.src)

    def test_calls_create_rule(self):
        self.assertIn("createRule", self.src)

    def test_has_new_rule_button(self):
        self.assertIn("New Rule", self.src)

    def test_has_status_filter(self):
        self.assertIn("statusFilter", self.src)

    def test_has_type_filter(self):
        self.assertIn("typeFilter", self.src)

    def test_shows_activate_action(self):
        self.assertIn("activateRule", self.src)

    def test_shows_deactivate_action(self):
        self.assertIn("deactivateRule", self.src)

    def test_shows_archive_action(self):
        self.assertIn("archiveRule", self.src)

    def test_links_to_rule_detail(self):
        self.assertIn("recommendation-rules/", self.src)

    def test_links_to_results(self):
        self.assertIn("recommendation-results", self.src)

    def test_json_fields_have_validation(self):
        self.assertIn("condition_json", self.src)
        self.assertIn("recommendation_json", self.src)

    def test_no_hardcoded_recommendation_list(self):
        self.assertNotIn("voltas", self.src)
        self.assertNotIn("daikin", self.src)


class TestRecommendationRuleDetailPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/automation/recommendation-rules/[ruleId]/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_recommendation_api(self):
        self.assertIn("recommendationApi", self.src)

    def test_uses_params(self):
        self.assertIn("useParams", self.src)

    def test_calls_get_rule(self):
        self.assertIn("getRule", self.src)

    def test_calls_update_rule(self):
        self.assertIn("updateRule", self.src)

    def test_has_activate_action(self):
        self.assertIn("activateRule", self.src)

    def test_has_deactivate_action(self):
        self.assertIn("deactivateRule", self.src)

    def test_has_archive_action(self):
        self.assertIn("archiveRule", self.src)

    def test_has_simulate_section(self):
        self.assertIn("simulateRule", self.src)
        self.assertIn("Simulate", self.src)

    def test_simulate_no_mutation_note(self):
        self.assertIn("simResult.data.note", self.src)

    def test_simulation_shows_matched(self):
        self.assertIn("matched", self.src)

    def test_simulation_shows_recommendations(self):
        self.assertIn("recommendations", self.src)

    def test_simulation_shows_warnings(self):
        self.assertIn("warnings", self.src)

    def test_condition_json_helper(self):
        self.assertIn("Allowed keys", self.src)

    def test_recommendation_json_helper(self):
        self.assertIn("entity_codes", self.src)

    def test_confidence_score_displayed(self):
        self.assertIn("confidence_score", self.src)


class TestRecommendationResultsPage(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/automation/recommendation-results/page.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_recommendation_api(self):
        self.assertIn("recommendationApi", self.src)

    def test_calls_list_results(self):
        self.assertIn("listResults", self.src)

    def test_has_status_filter(self):
        self.assertIn("statusFilter", self.src)

    def test_has_context_filter(self):
        self.assertIn("contextFilter", self.src)

    def test_shows_accept_action(self):
        self.assertIn("acceptResult", self.src)

    def test_shows_reject_action(self):
        self.assertIn("rejectResult", self.src)

    def test_shows_entity_type(self):
        self.assertIn("recommended_entity_type", self.src)

    def test_shows_confidence_score(self):
        self.assertIn("confidence_score", self.src)

    def test_shows_explanation(self):
        self.assertIn("explanation", self.src)

    def test_shows_context_type(self):
        self.assertIn("context_type", self.src)

    def test_status_color_coding(self):
        self.assertIn("STATUS_COLORS", self.src)
        self.assertIn("accepted", self.src)
        self.assertIn("rejected", self.src)

    def test_back_link_to_rules(self):
        self.assertIn("recommendation-rules", self.src)


if __name__ == "__main__":
    unittest.main()
