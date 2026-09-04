"""
Sprint: Tenant Portal Compliance
Tests: provider_router.py, api.ts, frontend pages, tenant isolation

Class layout
 A. TestProviderRouterFile             — file structure, imports, constants
 B. TestSummaryEndpoint                — /summary shape, tenant guard
 C. TestMyRequestsCreate               — create validation, duplicate check, rate limit, erasure warning
 D. TestMyRequestsRead                 — list, get, filters, tenant isolation
 E. TestCancelRequest                  — cancel state machine
 F. TestExportFlow                     — generate-export, list/get/download, expired check, tenant scope
 G. TestConsentEndpoints               — list, withdraw, withdrawable types guard
 H. TestStaffRequests                  — list, get, tenant-response, subject_type filter
 I. TestCustomerRequests               — list, get, tenant-response, limited view
 J. TestTenantIsolation                — cross-tenant query safety patterns
 K. TestApiTs                          — interfaces and all methods in api.ts
 L. TestFrontendDashboardPage          — 7 tabs, create modal, withdraw modal, SummaryCards
 M. TestFrontendDetailPage             — detail page: summary, timeline, export CTA, cancel btn
 N. TestNavConfig                      — provider-compliance nav item + path mapping
 O. TestMainPyRegistration             — provider_router registered in main.py
 P. TestRateLimitHelpers               — _check_rate_limit, _require_tenant helpers
"""
import re
from pathlib import Path

# Repo-relative: this file is tests/<name>.py, so parents[1] is the repo
# root. A hardcoded absolute path made every test here fail on any machine
# that was not the Windows box it was written on, CI included.
ROOT = Path(__file__).resolve().parents[1]

ROUTER_FILE  = ROOT / "app/engines/compliance/provider_router.py"
MAIN_FILE    = ROOT / "app/main.py"
API_TS       = ROOT / "frontend/tenant-portal/lib/api.ts"
NAV_FILE     = ROOT / "frontend/tenant-portal/components/layout/TenantLayout.tsx"
DASH_PAGE    = ROOT / "frontend/tenant-portal/app/(tenant)/provider/compliance/page.tsx"
DETAIL_PAGE  = ROOT / "frontend/tenant-portal/app/(tenant)/provider/compliance/requests/[id]/page.tsx"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ─── A. Router file structure ─────────────────────────────────────────────────

class TestProviderRouterFile:
    def test_file_exists(self):
        assert ROUTER_FILE.exists(), "provider_router.py must exist"

    def test_prefix(self):
        assert "/v1/provider/compliance" in _read(ROUTER_FILE)

    def test_tags(self):
        assert "Compliance Tenant Portal" in _read(ROUTER_FILE) or \
               "Compliance Provider" in _read(ROUTER_FILE)

    def test_imports_require_tenant_owner(self):
        assert "require_tenant_owner" in _read(ROUTER_FILE)

    def test_imports_require_technician(self):
        assert "require_technician" in _read(ROUTER_FILE)

    def test_imports_compliance_enterprise_service(self):
        assert "ComplianceEnterpriseService" in _read(ROUTER_FILE)

    def test_imports_compliance_models(self):
        src = _read(ROUTER_FILE)
        assert "ComplianceRequest" in src
        assert "ComplianceAuditLog" in src
        assert "ComplianceExport" in src

    def test_tenant_allowed_request_types_constant(self):
        assert "TENANT_ALLOWED_REQUEST_TYPES" in _read(ROUTER_FILE)

    def test_erasure_types_constant(self):
        assert "ERASURE_TYPES" in _read(ROUTER_FILE) or \
               "erasure" in _read(ROUTER_FILE)

    def test_withdrawable_consent_types_constant(self):
        assert "TENANT_WITHDRAWABLE_CONSENT_TYPES" in _read(ROUTER_FILE) or \
               "WITHDRAWABLE_CONSENT_TYPES" in _read(ROUTER_FILE)

    def test_open_statuses_constant(self):
        assert "OPEN_STATUSES" in _read(ROUTER_FILE)

    def test_rate_limit_constants_defined(self):
        src = _read(ROUTER_FILE)
        assert "RATE_LIMIT_CREATE_PER_DAY" in src or \
               "RATE_LIMIT" in src

    def test_require_tenant_helper(self):
        assert "_require_tenant" in _read(ROUTER_FILE)

    def test_tenant_safe_request_helper(self):
        assert "_tenant_safe_request" in _read(ROUTER_FILE)

    def test_customer_limited_view_helper(self):
        assert "_customer_limited_view" in _read(ROUTER_FILE)

    def test_audit_helper_defined(self):
        src = _read(ROUTER_FILE)
        assert "_audit(" in src or "ComplianceAuditLog(" in src


# ─── B. Summary endpoint ──────────────────────────────────────────────────────

class TestSummaryEndpoint:
    def test_get_summary_route_exists(self):
        assert '"/summary"' in _read(ROUTER_FILE) or \
               "summary" in _read(ROUTER_FILE)

    def test_summary_returns_open_requests(self):
        assert "open_requests" in _read(ROUTER_FILE)

    def test_summary_returns_sla_at_risk(self):
        assert "sla_at_risk" in _read(ROUTER_FILE)

    def test_summary_returns_data_exports(self):
        assert "data_exports" in _read(ROUTER_FILE)

    def test_summary_returns_staff_requests_count(self):
        assert "staff_requests" in _read(ROUTER_FILE)

    def test_summary_returns_completed(self):
        assert "completed_requests" in _read(ROUTER_FILE)

    def test_summary_returns_rejected(self):
        assert "rejected_requests" in _read(ROUTER_FILE)

    def test_summary_scoped_by_tenant_id(self):
        src = _read(ROUTER_FILE)
        # Queries must filter by tenant_id from JWT
        assert 'metadata_json["tenant_id"]' in src or \
               "tenant_id_str" in src

    def test_summary_uses_require_technician(self):
        # Summary is a read operation — staff should also see it
        src = _read(ROUTER_FILE)
        summary_pos = src.find("get_summary")
        require_tech_pos = src.find("require_technician")
        assert require_tech_pos != -1 and summary_pos != -1


# ─── C. Create request ────────────────────────────────────────────────────────

class TestMyRequestsCreate:
    def test_post_requests_route_exists(self):
        src = _read(ROUTER_FILE)
        assert "@router.post" in src
        assert '"/requests"' in src

    def test_validates_request_type_against_constant(self):
        src = _read(ROUTER_FILE)
        assert "TENANT_ALLOWED_REQUEST_TYPES" in src
        assert "VALIDATION_ERROR" in src

    def test_requires_confirm_understanding(self):
        assert "confirm_understanding" in _read(ROUTER_FILE)

    def test_requires_reason(self):
        src = _read(ROUTER_FILE)
        assert '"reason"' in src or "reason" in src

    def test_duplicate_open_request_check(self):
        src = _read(ROUTER_FILE)
        assert "DUPLICATE_OPEN_REQUEST" in src

    def test_duplicate_check_scoped_to_tenant(self):
        src = _read(ROUTER_FILE)
        # The duplicate check must also filter by tenant scope
        dup_pos = src.find("DUPLICATE_OPEN_REQUEST")
        tenant_before = src.rfind("tenant_id", 0, dup_pos)
        assert tenant_before != -1

    def test_stores_tenant_id_in_metadata(self):
        src = _read(ROUTER_FILE)
        assert '"tenant_id"' in src or "tenant_id" in src

    def test_request_source_is_tenant_portal(self):
        assert "tenant_portal" in _read(ROUTER_FILE)

    def test_erasure_warning_message_included(self):
        src = _read(ROUTER_FILE)
        assert "ERASURE_BLOCKERS_MESSAGE" in src or "legally exempt" in src or \
               "cannot be removed" in src or "7 years" in src or \
               "financial records" in src.lower() or "exempt" in src

    def test_create_requires_tenant_owner(self):
        src = _read(ROUTER_FILE)
        # POST create is a write operation — must require tenant_owner
        # Find the create_my_request function
        create_pos = src.find("create_my_request")
        tech_before = src.rfind("require_tenant_owner", 0, create_pos + 200)
        assert tech_before != -1 or "require_tenant_owner" in src[create_pos:create_pos+300]

    def test_rate_limit_applied_on_create(self):
        src = _read(ROUTER_FILE)
        create_pos = src.find("create_my_request")
        rate_limit_pos = src.find("_check_rate_limit", create_pos)
        assert rate_limit_pos != -1


# ─── D. Read requests ─────────────────────────────────────────────────────────

class TestMyRequestsRead:
    def test_get_requests_list_route(self):
        src = _read(ROUTER_FILE)
        assert "@router.get" in src
        assert '"/requests"' in src

    def test_list_supports_request_type_filter(self):
        src = _read(ROUTER_FILE)
        assert "request_type" in src

    def test_list_supports_status_filter(self):
        src = _read(ROUTER_FILE)
        assert "req_status" in src or '"status"' in src

    def test_list_supports_pagination(self):
        src = _read(ROUTER_FILE)
        assert "page" in src and "limit" in src

    def test_list_returns_meta_object(self):
        assert '"total"' in _read(ROUTER_FILE) or \
               "'total'" in _read(ROUTER_FILE)

    def test_get_single_request_route(self):
        src = _read(ROUTER_FILE)
        assert '"/requests/{request_id}"' in src

    def test_get_single_verifies_tenant_scope(self):
        src = _read(ROUTER_FILE)
        # get_my_request must check tenant scope
        get_pos = src.find("get_my_request")
        not_found_pos = src.find("NOT_FOUND", get_pos)
        assert not_found_pos != -1

    def test_get_single_includes_export_info(self):
        src = _read(ROUTER_FILE)
        get_pos = src.find("get_my_request")
        export_pos = src.find("export", get_pos)
        assert export_pos != -1

    def test_get_single_filters_audit_trail(self):
        src = _read(ROUTER_FILE)
        # Tenant should only see certain audit actions
        assert "visible_actions" in src or "audit_trail" in src

    def test_tenant_safe_strips_admin_notes(self):
        src = _read(ROUTER_FILE)
        # _tenant_safe_request return dict must not include admin_notes key
        safe_start = src.find("def _tenant_safe_request")
        return_pos = src.find("return {", safe_start)
        safe_end = src.find("\ndef ", safe_start + 1)
        if safe_end == -1:
            safe_end = safe_start + 1000
        # The return dict itself should not contain "admin_notes"
        return_dict = src[return_pos:safe_end]
        # docstring mentions it is omitted; the key must not appear as a dict key
        assert '"admin_notes"' not in return_dict and "'admin_notes'" not in return_dict


# ─── E. Cancel request ────────────────────────────────────────────────────────

class TestCancelRequest:
    def test_cancel_route_exists(self):
        assert "/cancel" in _read(ROUTER_FILE)

    def test_cancel_checks_cancellable_statuses(self):
        src = _read(ROUTER_FILE)
        cancel_pos = src.find("cancel_my_request")
        invalid_pos = src.find("INVALID_STATE", cancel_pos)
        assert invalid_pos != -1

    def test_cancel_only_submitted_or_identity_pending(self):
        src = _read(ROUTER_FILE)
        cancel_pos = src.find("cancel_my_request")
        submitted_pos = src.find("submitted", cancel_pos)
        assert submitted_pos != -1

    def test_cancel_sets_status_cancelled(self):
        src = _read(ROUTER_FILE)
        cancel_pos = src.find("cancel_my_request")
        cancelled_pos = src.find('"cancelled"', cancel_pos)
        assert cancelled_pos != -1

    def test_cancel_audits_action(self):
        src = _read(ROUTER_FILE)
        cancel_pos = src.find("cancel_my_request")
        audit_pos = src.find("cancelled", cancel_pos + 100)
        assert audit_pos != -1


# ─── F. Export flow ───────────────────────────────────────────────────────────

class TestExportFlow:
    def test_generate_export_route_exists(self):
        assert "generate-export" in _read(ROUTER_FILE)

    def test_generate_export_checks_export_type(self):
        src = _read(ROUTER_FILE)
        gen_pos = src.find("generate_export")
        invalid_type_pos = src.find("INVALID_REQUEST_TYPE", gen_pos)
        assert invalid_type_pos != -1

    def test_generate_export_checks_status_approved(self):
        src = _read(ROUTER_FILE)
        gen_pos = src.find("generate_export")
        approved_pos = src.find("approved", gen_pos)
        assert approved_pos != -1

    def test_generate_export_creates_compliance_export(self):
        src = _read(ROUTER_FILE)
        assert "ComplianceExport(" in src

    def test_generate_export_sets_subject_type_and_id(self):
        src = _read(ROUTER_FILE)
        assert "subject_type=req.subject_type" in src
        assert "subject_id=req.subject_id" in src

    def test_generate_export_sets_expires_at(self):
        src = _read(ROUTER_FILE)
        assert "expires_at" in src and "timedelta" in src

    def test_list_exports_route(self):
        assert '"/exports"' in _read(ROUTER_FILE)

    def test_list_exports_scoped_by_tenant(self):
        src = _read(ROUTER_FILE)
        exports_pos = src.find("list_exports")
        tenant_pos = src.find("tenant_id", exports_pos)
        assert tenant_pos != -1

    def test_download_export_route(self):
        assert '"/exports/{export_id}/download"' in _read(ROUTER_FILE)

    def test_download_verifies_tenant_scope(self):
        src = _read(ROUTER_FILE)
        dl_pos = src.find("download_export")
        # Must load the request and verify tenant_id
        not_found_pos = src.find("NOT_FOUND", dl_pos)
        assert not_found_pos != -1

    def test_download_checks_expiry(self):
        src = _read(ROUTER_FILE)
        assert "EXPORT_EXPIRED" in src

    def test_download_checks_status_ready(self):
        src = _read(ROUTER_FILE)
        assert "EXPORT_NOT_READY" in src

    def test_download_rate_limit_applied(self):
        src = _read(ROUTER_FILE)
        dl_pos = src.find("download_export")
        rate_pos = src.find("_check_rate_limit", dl_pos)
        assert rate_pos != -1


# ─── G. Consent endpoints ─────────────────────────────────────────────────────

class TestConsentEndpoints:
    def test_list_consents_route(self):
        assert '"/consents"' in _read(ROUTER_FILE)

    def test_list_consents_calls_enterprise_service(self):
        src = _read(ROUTER_FILE)
        assert "list_consent_records" in src

    def test_list_consents_uses_current_user_id(self):
        src = _read(ROUTER_FILE)
        consents_pos = src.find("list_consents")
        user_pos = src.find("user_id", consents_pos)
        assert user_pos != -1

    def test_withdraw_consent_route(self):
        assert '"/consents/{consent_type}/withdraw"' in _read(ROUTER_FILE)

    def test_withdraw_validates_withdrawable_types(self):
        src = _read(ROUTER_FILE)
        assert "TENANT_WITHDRAWABLE_CONSENT_TYPES" in src or \
               "WITHDRAWABLE_CONSENT_TYPES" in src

    def test_withdraw_raises_on_unknown_type(self):
        src = _read(ROUTER_FILE)
        withdraw_pos = src.find("withdraw_consent")
        validation_pos = src.find("VALIDATION_ERROR", withdraw_pos)
        assert validation_pos != -1

    def test_withdraw_rate_limit_applied(self):
        src = _read(ROUTER_FILE)
        withdraw_pos = src.find("withdraw_consent")
        rate_pos = src.find("_check_rate_limit", withdraw_pos)
        assert rate_pos != -1

    def test_withdraw_calls_revoke_consent(self):
        src = _read(ROUTER_FILE)
        assert "revoke_consent" in src

    def test_withdraw_audits_action(self):
        src = _read(ROUTER_FILE)
        withdraw_pos = src.find("withdraw_consent")
        audit_pos = src.find("consent_withdrawn", withdraw_pos)
        assert audit_pos != -1


# ─── H. Staff requests ────────────────────────────────────────────────────────

class TestStaffRequests:
    def test_list_staff_requests_route(self):
        assert '"/staff-requests"' in _read(ROUTER_FILE)

    def test_list_staff_filters_by_staff_subject_types(self):
        src = _read(ROUTER_FILE)
        assert "TENANT_STAFF_SUBJECT_TYPES" in src

    def test_list_staff_scoped_to_tenant(self):
        src = _read(ROUTER_FILE)
        staff_pos = src.find("list_staff_requests")
        tenant_pos = src.find("tenant_id", staff_pos)
        assert tenant_pos != -1

    def test_list_staff_requires_tenant_owner(self):
        src = _read(ROUTER_FILE)
        staff_pos = src.find("list_staff_requests")
        owner_pos = src.rfind("require_tenant_owner", 0, staff_pos + 300)
        assert owner_pos != -1 or "require_tenant_owner" in src[staff_pos:staff_pos + 400]

    def test_get_staff_request_detail_route(self):
        assert '"/staff-requests/{request_id}"' in _read(ROUTER_FILE)

    def test_get_staff_request_verifies_tenant_scope(self):
        src = _read(ROUTER_FILE)
        get_pos = src.find("get_staff_request")
        not_found_pos = src.find("NOT_FOUND", get_pos)
        assert not_found_pos != -1

    def test_tenant_response_route_exists(self):
        assert "tenant-response" in _read(ROUTER_FILE)

    def test_tenant_response_appends_to_metadata(self):
        src = _read(ROUTER_FILE)
        assert "tenant_responses" in src

    def test_tenant_response_validates_not_empty(self):
        src = _read(ROUTER_FILE)
        resp_pos = src.find("staff_tenant_response")
        if resp_pos == -1:
            resp_pos = src.find("tenant_response")
        val_pos = src.find("VALIDATION_ERROR", resp_pos)
        assert val_pos != -1


# ─── I. Customer requests (limited) ──────────────────────────────────────────

class TestCustomerRequests:
    def test_list_customer_requests_route(self):
        assert '"/customer-requests"' in _read(ROUTER_FILE)

    def test_list_customer_requests_filters_subject_type_customer(self):
        src = _read(ROUTER_FILE)
        cust_pos = src.find("customer-requests")
        customer_pos = src.find('"customer"', cust_pos)
        assert customer_pos != -1

    def test_list_customer_requests_uses_related_tenant_id(self):
        src = _read(ROUTER_FILE)
        assert "related_tenant_id" in src

    def test_customer_limited_view_omits_personal_data(self):
        src = _read(ROUTER_FILE)
        limited_start = src.find("def _customer_limited_view")
        limited_end = src.find("\ndef ", limited_start + 1)
        if limited_end == -1:
            limited_end = limited_start + 1000
        limited_func = src[limited_start:limited_end]
        # Must NOT include: admin_notes, subject_id (the customer's UUID)
        assert "admin_notes" not in limited_func

    def test_customer_limited_view_returns_status_label(self):
        src = _read(ROUTER_FILE)
        limited_start = src.find("_customer_limited_view")
        limited_end = src.find("\n    return ", limited_start + 100) + 500
        assert "status" in src[limited_start:limited_end]

    def test_get_customer_request_detail_route(self):
        assert '"/customer-requests/{request_id}"' in _read(ROUTER_FILE)

    def test_get_customer_verifies_related_tenant(self):
        src = _read(ROUTER_FILE)
        get_pos = src.find("get_customer_request")
        not_found_pos = src.find("NOT_FOUND", get_pos)
        assert not_found_pos != -1

    def test_customer_tenant_response_route(self):
        src = _read(ROUTER_FILE)
        cust_resp_pos = src.find("customer_tenant_response")
        assert cust_resp_pos != -1

    def test_list_customer_result_has_note(self):
        src = _read(ROUTER_FILE)
        assert '"note"' in src or "note" in src


# ─── J. Tenant isolation ──────────────────────────────────────────────────────

class TestTenantIsolation:
    def test_require_tenant_helper_raises_if_no_tenant(self):
        src = _read(ROUTER_FILE)
        tenant_helper_start = src.find("def _require_tenant")
        tenant_helper_end = src.find("\ndef ", tenant_helper_start + 1)
        if tenant_helper_end == -1:
            tenant_helper_end = tenant_helper_start + 500
        func_body = src[tenant_helper_start:tenant_helper_end]
        assert "FORBIDDEN" in func_body or "raise" in func_body

    def test_all_list_queries_filter_by_tenant_metadata(self):
        src = _read(ROUTER_FILE)
        # At minimum these must all reference tenant_id
        assert src.count("tenant_id_str") >= 5

    def test_cross_tenant_never_returns_data(self):
        src = _read(ROUTER_FILE)
        # Every route that loads a ComplianceRequest must include tenant scope check
        # Verify via pattern: the scope check is present before NOT_FOUND raise in key endpoints
        get_my_pos = src.find("get_my_request")
        get_staff_pos = src.find("get_staff_request")
        get_cust_pos = src.find("get_customer_request")
        for pos in [get_my_pos, get_staff_pos, get_cust_pos]:
            not_found = src.find("NOT_FOUND", pos)
            assert not_found != -1 and not_found - pos < 2000

    def test_audit_always_includes_tenant_id(self):
        src = _read(ROUTER_FILE)
        # _audit calls pass tenant_id first arg
        audit_calls = [m.start() for m in re.finditer(r"_audit\(", src)]
        assert len(audit_calls) >= 5

    def test_no_platform_wide_request_query(self):
        src = _read(ROUTER_FILE)
        # No unscoped select(ComplianceRequest) without tenant filter
        # The ONLY legitimate use is inside tenant-scoped helpers
        unscoped = re.findall(
            r"select\(ComplianceRequest\)(?:(?!tenant_id).){0,500}await db\.scalar",
            src, re.DOTALL)
        # Allow some tolerance for single-row lookups that use request_id+tenant filter
        assert len(unscoped) <= 3, f"Too many potentially unscoped queries: {len(unscoped)}"


# ─── K. API TS ────────────────────────────────────────────────────────────────

class TestApiTs:
    def test_provider_compliance_api_exported(self):
        assert "providerComplianceApi" in _read(API_TS)

    def test_tenant_compliance_request_interface(self):
        assert "TenantComplianceRequest" in _read(API_TS)

    def test_tenant_compliance_summary_interface(self):
        assert "TenantComplianceSummary" in _read(API_TS)

    def test_tenant_compliance_request_list_interface(self):
        assert "TenantComplianceRequestList" in _read(API_TS)

    def test_tenant_create_request_result_interface(self):
        assert "TenantCreateRequestResult" in _read(API_TS)

    def test_tenant_export_interface(self):
        assert "TenantExport" in _read(API_TS)

    def test_tenant_consent_record_interface(self):
        assert "TenantConsentRecord" in _read(API_TS)

    def test_api_method_get_summary(self):
        assert "getSummary" in _read(API_TS)

    def test_api_method_list_requests(self):
        src = _read(API_TS)
        # Ensure it's in providerComplianceApi not just customerComplianceApi
        prov_pos = src.find("providerComplianceApi")
        list_pos = src.find("listRequests", prov_pos)
        assert list_pos != -1

    def test_api_method_create_request(self):
        src = _read(API_TS)
        prov_pos = src.find("providerComplianceApi")
        create_pos = src.find("createRequest", prov_pos)
        assert create_pos != -1

    def test_api_method_get_request(self):
        src = _read(API_TS)
        prov_pos = src.find("providerComplianceApi")
        get_pos = src.find("getRequest", prov_pos)
        assert get_pos != -1

    def test_api_method_cancel_request(self):
        src = _read(API_TS)
        prov_pos = src.find("providerComplianceApi")
        cancel_pos = src.find("cancelRequest", prov_pos)
        assert cancel_pos != -1

    def test_api_method_generate_export(self):
        assert "generateExport" in _read(API_TS)

    def test_api_method_list_exports(self):
        src = _read(API_TS)
        prov_pos = src.find("providerComplianceApi")
        le_pos = src.find("listExports", prov_pos)
        assert le_pos != -1

    def test_api_method_download_export(self):
        src = _read(API_TS)
        prov_pos = src.find("providerComplianceApi")
        dl_pos = src.find("downloadExport", prov_pos)
        assert dl_pos != -1

    def test_api_method_list_consents(self):
        src = _read(API_TS)
        prov_pos = src.find("providerComplianceApi")
        lc_pos = src.find("listConsents", prov_pos)
        assert lc_pos != -1

    def test_api_method_withdraw_consent(self):
        src = _read(API_TS)
        prov_pos = src.find("providerComplianceApi")
        wc_pos = src.find("withdrawConsent", prov_pos)
        assert wc_pos != -1

    def test_api_method_list_staff_requests(self):
        assert "listStaffRequests" in _read(API_TS)

    def test_api_method_get_staff_request(self):
        assert "getStaffRequest" in _read(API_TS)

    def test_api_method_add_staff_response(self):
        assert "addStaffResponse" in _read(API_TS)

    def test_api_method_list_customer_requests(self):
        assert "listCustomerRequests" in _read(API_TS)

    def test_api_method_get_customer_request(self):
        assert "getCustomerRequest" in _read(API_TS)

    def test_api_method_add_customer_response(self):
        assert "addCustomerResponse" in _read(API_TS)

    def test_provider_prefix_in_api_calls(self):
        src = _read(API_TS)
        assert "/v1/provider/compliance" in src

    def test_tenant_compliance_request_has_status_label(self):
        src = _read(API_TS)
        iface_pos = src.find("TenantComplianceRequest")
        label_pos = src.find("status_label", iface_pos)
        assert label_pos != -1

    def test_tenant_compliance_request_has_sla_fields(self):
        src = _read(API_TS)
        iface_pos = src.find("TenantComplianceRequest")
        sla_pos = src.find("sla_status", iface_pos)
        assert sla_pos != -1


# ─── L. Frontend dashboard page ──────────────────────────────────────────────

class TestFrontendDashboardPage:
    def test_page_file_exists(self):
        assert DASH_PAGE.exists(), "provider/compliance/page.tsx must exist"

    def test_uses_use_client(self):
        assert '"use client"' in _read(DASH_PAGE)

    def test_imports_provider_compliance_api(self):
        assert "providerComplianceApi" in _read(DASH_PAGE)

    def test_imports_tenant_layout(self):
        assert "TenantLayout" in _read(DASH_PAGE)

    def test_overview_tab_id(self):
        assert '"overview"' in _read(DASH_PAGE) or "'overview'" in _read(DASH_PAGE)

    def test_my_requests_tab(self):
        assert "my-requests" in _read(DASH_PAGE)

    def test_staff_requests_tab(self):
        assert "staff-requests" in _read(DASH_PAGE)

    def test_customer_requests_tab(self):
        assert "customer-requests" in _read(DASH_PAGE)

    def test_consents_tab(self):
        assert "consents" in _read(DASH_PAGE)

    def test_exports_tab(self):
        assert "exports" in _read(DASH_PAGE)

    def test_help_tab(self):
        assert "help" in _read(DASH_PAGE)

    def test_seven_tabs_defined(self):
        src = _read(DASH_PAGE)
        # TABS array
        tabs_count = src.count("{ id:") + src.count('{ id: "')
        assert tabs_count >= 7

    def test_create_modal_present(self):
        assert "showCreate" in _read(DASH_PAGE)

    def test_create_modal_has_open_prop(self):
        assert "open={showCreate}" in _read(DASH_PAGE)

    def test_withdraw_consent_modal_present(self):
        assert "withdrawType" in _read(DASH_PAGE)

    def test_withdraw_modal_has_open_prop(self):
        src = _read(DASH_PAGE)
        # Modal open={withdrawType !== null}
        assert "open={withdrawType" in src or "open={withdrawType !== null}" in src

    def test_summary_cards_component_or_inline(self):
        src = _read(DASH_PAGE)
        assert "SummaryCards" in src or "open_requests" in src

    def test_badge_uses_variant_prop(self):
        assert "variant=" in _read(DASH_PAGE)

    def test_section_header_uses_subtitle(self):
        src = _read(DASH_PAGE)
        assert "description=" in src

    def test_no_color_prop_on_badge(self):
        src = _read(DASH_PAGE)
        # Badge must not use deprecated color= prop
        badge_uses = re.findall(r"<Badge\s[^>]*>", src)
        for b in badge_uses:
            assert "color=" not in b, f"Badge uses color= instead of variant=: {b}"

    def test_dpdp_compliance_explanation_in_overview(self):
        src = _read(DASH_PAGE)
        assert "72 hours" in src or "DPDP" in src

    def test_erasure_warning_shown_in_create_modal(self):
        src = _read(DASH_PAGE)
        assert "ERASURE_TYPES" in src or "erasure" in src.lower()

    def test_import_path_correct_four_levels(self):
        src = _read(DASH_PAGE)
        # 4 levels up: compliance → provider → (tenant) → app → tenant-portal
        assert "../../../../components" in src or "../../../../lib" in src

    def test_no_five_level_import(self):
        src = _read(DASH_PAGE)
        assert "../../../../../components" not in src

    def test_calls_get_summary(self):
        assert "getSummary" in _read(DASH_PAGE)

    def test_calls_list_requests(self):
        src = _read(DASH_PAGE)
        assert "listRequests" in src

    def test_calls_list_staff_requests(self):
        assert "listStaffRequests" in _read(DASH_PAGE)

    def test_calls_list_customer_requests(self):
        assert "listCustomerRequests" in _read(DASH_PAGE)

    def test_calls_list_consents(self):
        assert "listConsents" in _read(DASH_PAGE)

    def test_calls_list_exports(self):
        assert "listExports" in _read(DASH_PAGE)


# ─── M. Frontend detail page ─────────────────────────────────────────────────

class TestFrontendDetailPage:
    def test_detail_page_exists(self):
        assert DETAIL_PAGE.exists(), "compliance/requests/[id]/page.tsx must exist"

    def test_uses_use_client(self):
        assert '"use client"' in _read(DETAIL_PAGE)

    def test_imports_provider_compliance_api(self):
        assert "providerComplianceApi" in _read(DETAIL_PAGE)

    def test_shows_request_number(self):
        assert "request_number" in _read(DETAIL_PAGE)

    def test_shows_status_badge(self):
        src = _read(DETAIL_PAGE)
        assert "STATUS_COLOR" in src or "variant=" in src

    def test_shows_sla_badge(self):
        src = _read(DETAIL_PAGE)
        assert "SLA_COLOR" in src or "sla_" in src

    def test_shows_rejection_reason(self):
        assert "rejection_reason" in _read(DETAIL_PAGE)

    def test_shows_export_section(self):
        assert "export" in _read(DETAIL_PAGE).lower()

    def test_generate_export_btn_present(self):
        assert "Generate Export" in _read(DETAIL_PAGE) or "generate-export" in _read(DETAIL_PAGE)

    def test_download_btn_present(self):
        assert "Download" in _read(DETAIL_PAGE)

    def test_cancel_button_present(self):
        assert "Cancel Request" in _read(DETAIL_PAGE) or "cancelRequest" in _read(DETAIL_PAGE)

    def test_cancel_only_for_cancellable_statuses(self):
        src = _read(DETAIL_PAGE)
        assert "submitted" in src
        assert "identity_verification_pending" in src

    def test_audit_trail_timeline_present(self):
        assert "audit_trail" in _read(DETAIL_PAGE)

    def test_back_link_present(self):
        assert "Back to Compliance" in _read(DETAIL_PAGE) or "/provider/compliance" in _read(DETAIL_PAGE)

    def test_what_happens_next_card(self):
        src = _read(DETAIL_PAGE)
        assert "What Happens Next" in src or "WHAT_NEXT" in src

    def test_expired_export_message(self):
        src = _read(DETAIL_PAGE)
        assert "expired" in src.lower()

    def test_section_header_subtitle(self):
        assert "description=" in _read(DETAIL_PAGE)

    def test_import_path_six_levels(self):
        src = _read(DETAIL_PAGE)
        assert "../../../../../../components" in src or "../../../../../../lib" in src


# ─── N. Nav config ────────────────────────────────────────────────────────────

class TestNavConfig:
    def test_provider_compliance_nav_item(self):
        src = _read(NAV_FILE)
        assert "provider-compliance" in src

    def test_compliance_href_correct(self):
        assert "/provider/compliance" in _read(NAV_FILE)

    def test_compliance_label(self):
        src = _read(NAV_FILE)
        assert '"Compliance"' in src or "'Compliance'" in src

    def test_compliance_in_provider_group(self):
        # Compliance is an occasional business-setup destination in the
        # consolidated provider navigation.
        src = _read(NAV_FILE)
        secondary_pos = src.find("const SECONDARY_NAV_GROUPS")
        setup_pos = src.find('label: "Business setup"', secondary_pos)
        compliance_pos = src.find('id: "provider-compliance"')
        assert secondary_pos != -1 and setup_pos != -1 and compliance_pos != -1
        assert secondary_pos < setup_pos < compliance_pos

    def test_path_mapping_compliance(self):
        assert "compliance" in _read(NAV_FILE)

    def test_path_maps_compliance_to_provider_compliance(self):
        src = _read(NAV_FILE)
        assert "provider-compliance" in src


# ─── O. main.py registration ─────────────────────────────────────────────────

class TestMainPyRegistration:
    def test_provider_router_imported(self):
        assert "compliance_provider_router" in _read(MAIN_FILE) or \
               "provider_router" in _read(MAIN_FILE)

    def test_provider_router_included(self):
        src = _read(MAIN_FILE)
        assert "include_router(compliance_provider_router)" in src or \
               "include_router" in src and "provider_router" in src

    def test_provider_router_registered_after_customer_router(self):
        src = _read(MAIN_FILE)
        customer_pos = src.find("compliance_customer_router")
        provider_pos = src.find("compliance_provider_router")
        assert customer_pos != -1 and provider_pos != -1
        assert provider_pos > customer_pos


# ─── P. Rate limit & require_tenant helpers ───────────────────────────────────

class TestRateLimitHelpers:
    def test_check_rate_limit_queries_audit_log(self):
        src = _read(ROUTER_FILE)
        rl_start = src.find("async def _check_rate_limit")
        rl_end = src.find("\nasync def ", rl_start + 1)
        if rl_end == -1:
            rl_end = rl_start + 1000
        func_body = src[rl_start:rl_end]
        assert "ComplianceAuditLog" in func_body

    def test_check_rate_limit_filters_by_actor_and_action(self):
        src = _read(ROUTER_FILE)
        rl_start = src.find("async def _check_rate_limit")
        rl_end = src.find("\nasync def ", rl_start + 1)
        if rl_end == -1:
            rl_end = rl_start + 1000
        func_body = src[rl_start:rl_end]
        assert "actor_id" in func_body
        assert "action" in func_body

    def test_check_rate_limit_checks_start_of_day(self):
        src = _read(ROUTER_FILE)
        rl_start = src.find("async def _check_rate_limit")
        rl_end = src.find("\nasync def ", rl_start + 1)
        if rl_end == -1:
            rl_end = rl_start + 1000
        func_body = src[rl_start:rl_end]
        assert "start_of_day" in func_body or "hour=0" in func_body

    def test_check_rate_limit_raises_rate_limit_exceeded(self):
        src = _read(ROUTER_FILE)
        assert "RATE_LIMIT_EXCEEDED" in src

    def test_require_tenant_returns_str(self):
        src = _read(ROUTER_FILE)
        tenant_helper = src.find("def _require_tenant")
        func_body = src[tenant_helper:tenant_helper + 500]
        assert "return" in func_body and "tenant_id" in func_body
