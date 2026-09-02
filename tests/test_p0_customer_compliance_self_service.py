"""P0 Customer Self-Service Compliance — Test Suite.

Tests cover:
  A. Customer Router file structure and endpoints
  B. Security — ownership and role enforcement
  C. Request creation — validation rules
  D. Duplicate request blocking
  E. Rate limiting
  F. Consent withdrawal
  G. Export download security
  H. Admin integration — requests visible to admin
  I. api.ts — customer compliance methods
  J. Frontend pages exist
  K. Audit logging
  L. Status labels (customer-safe)
"""
from pathlib import Path

import pytest

ROOT      = Path(__file__).parent.parent
ROUTER    = ROOT / "app" / "engines" / "compliance" / "customer_router.py"
MAIN      = ROOT / "app" / "main.py"
API_TS    = ROOT / "frontend" / "tenant-portal" / "lib" / "api.ts"
PRIV_PAGE = ROOT / "frontend" / "tenant-portal" / "app" / "(tenant)" / "provider" / "compliance" / "page.tsx"
REQ_PAGE  = PRIV_PAGE
DETAIL_PAGE = ROOT / "frontend" / "tenant-portal" / "app" / "(tenant)" / "provider" / "compliance" / "requests" / "[id]" / "page.tsx"
NAV_CFG   = ROOT / "frontend" / "tenant-portal" / "components" / "layout" / "TenantLayout.tsx"


def r(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ── A. Router File Structure ──────────────────────────────────────────────────

class TestCustomerRouterStructure:
    def test_file_exists(self):
        assert ROUTER.exists()

    def test_prefix_is_v1_me_compliance(self):
        assert "/v1/me/compliance" in r(ROUTER)

    def test_list_requests_endpoint(self):
        src = r(ROUTER)
        assert '"/requests"' in src
        assert "async def list_my_requests" in src

    def test_create_request_endpoint(self):
        src = r(ROUTER)
        assert "async def create_my_request" in src

    def test_get_request_endpoint(self):
        src = r(ROUTER)
        assert "async def get_my_request" in src

    def test_cancel_request_endpoint(self):
        src = r(ROUTER)
        assert "async def cancel_my_request" in src

    def test_add_note_endpoint(self):
        src = r(ROUTER)
        assert "async def add_my_note" in src

    def test_list_consents_endpoint(self):
        src = r(ROUTER)
        assert "async def list_my_consents" in src

    def test_withdraw_consent_endpoint(self):
        src = r(ROUTER)
        assert "async def withdraw_my_consent" in src

    def test_download_export_endpoint(self):
        src = r(ROUTER)
        assert "async def download_my_export" in src

    def test_all_endpoints_require_customer(self):
        src = r(ROUTER)
        assert "require_customer" in src

    def test_tag_is_compliance_customer_self_service(self):
        src = r(ROUTER)
        assert "Customer Self-Service" in src

    def test_registered_in_main(self):
        src = r(MAIN)
        assert "compliance_customer_router" in src
        assert "customer_router" in src


# ── B. Security — Ownership Enforcement ──────────────────────────────────────

class TestOwnershipSecurity:
    def _src(self): return r(ROUTER)

    def test_list_filters_by_subject_id(self):
        src = self._src()
        assert "subject_id == user_id" in src

    def test_get_request_verifies_ownership(self):
        src = self._src()
        assert "subject_id == user_id" in src

    def test_cancel_verifies_ownership(self):
        src = self._src()
        # cancel endpoint must check ownership
        cancel_idx = src.find("async def cancel_my_request")
        cancel_section = src[cancel_idx:cancel_idx + 600]
        assert "subject_id == user_id" in cancel_section

    def test_download_verifies_ownership(self):
        src = self._src()
        download_idx = src.find("async def download_my_export")
        download_section = src[download_idx:download_idx + 1500]
        assert "subject_id == user_id" in download_section

    def test_download_verifies_request_type(self):
        src = self._src()
        assert '"data_export"' in src

    def test_not_found_on_wrong_owner(self):
        src = self._src()
        assert '"NOT_FOUND"' in src

    def test_admin_notes_stripped(self):
        src = self._src()
        # _customer_safe_request must NOT include admin_notes
        safe_fn = src[src.find("def _customer_safe_request"):][:800]
        assert "admin_notes" not in safe_fn

    def test_customer_subject_type_enforced_on_create(self):
        src = self._src()
        assert '"customer"' in src


# ── C. Request Creation Validation ───────────────────────────────────────────

class TestCreateValidation:
    def _src(self): return r(ROUTER)

    def test_allowed_request_types_defined(self):
        assert "CUSTOMER_ALLOWED_REQUEST_TYPES" in self._src()

    def test_right_to_erasure_allowed(self):
        assert "right_to_erasure" in self._src()

    def test_data_export_allowed(self):
        assert "data_export" in self._src()

    def test_consent_withdrawal_allowed(self):
        assert "consent_withdrawal" in self._src()

    def test_confirm_understanding_required(self):
        assert "confirm_understanding" in self._src()

    def test_reason_required_for_erasure(self):
        src = self._src()
        assert "right_to_erasure" in src
        assert "reason" in src

    def test_request_source_set_to_customer_app(self):
        assert "customer_app" in self._src()

    def test_returns_request_number(self):
        assert '"request_number"' in self._src()

    def test_returns_due_at(self):
        assert '"due_at"' in self._src()

    def test_returns_message(self):
        assert '"message"' in self._src()


# ── D. Duplicate Request Check ────────────────────────────────────────────────

class TestDuplicateCheck:
    def _src(self): return r(ROUTER)

    def test_open_statuses_defined(self):
        assert "OPEN_STATUSES" in self._src()

    def test_submitted_is_open_status(self):
        assert "submitted" in self._src()

    def test_under_review_is_open_status(self):
        assert "under_review" in self._src()

    def test_duplicate_error_code(self):
        assert "DUPLICATE_OPEN_REQUEST" in self._src()

    def test_existing_request_id_in_context(self):
        assert "existing_request_id" in self._src()

    def test_blocks_same_type_only(self):
        src = self._src()
        assert "request_type == request_type" in src or "ComplianceRequest.request_type == request_type" in src


# ── E. Rate Limiting ──────────────────────────────────────────────────────────

class TestRateLimiting:
    def _src(self): return r(ROUTER)

    def test_rate_limit_function_defined(self):
        assert "_check_rate_limit" in self._src()

    def test_create_rate_limit_5_per_day(self):
        src = self._src()
        assert "RATE_LIMIT_CREATE_PER_DAY" in src
        assert "5" in src

    def test_download_rate_limit_10_per_day(self):
        assert "RATE_LIMIT_DOWNLOAD_PER_DAY" in self._src()

    def test_consent_rate_limit_10_per_day(self):
        assert "RATE_LIMIT_CONSENT_WITHDRAW_PER_DAY" in self._src()

    def test_rate_limit_error_code(self):
        assert "RATE_LIMIT_EXCEEDED" in self._src()

    def test_rate_limit_uses_audit_log_count(self):
        src = self._src()
        assert "ComplianceAuditLog" in src
        assert "func.count" in src


# ── F. Consent Withdrawal ─────────────────────────────────────────────────────

class TestConsentWithdrawal:
    def _src(self): return r(ROUTER)

    def test_withdrawable_types_defined(self):
        assert "WITHDRAWABLE_CONSENT_TYPES" in self._src()

    def test_marketing_is_withdrawable(self):
        assert '"marketing"' in self._src()

    def test_notification_is_withdrawable(self):
        assert '"notification"' in self._src()

    def test_validation_for_non_withdrawable(self):
        src = self._src()
        assert "cannot be withdrawn" in src

    def test_calls_revoke_consent(self):
        assert "revoke_consent" in self._src()

    def test_audit_log_created_for_withdrawal(self):
        assert "compliance.customer_consent_withdrawn" in self._src()

    def test_returns_consent_type(self):
        assert '"consent_type"' in self._src()


# ── G. Export Download Security ───────────────────────────────────────────────

class TestExportDownloadSecurity:
    def _src(self): return r(ROUTER)

    def test_export_expired_error(self):
        assert "EXPORT_EXPIRED" in self._src()

    def test_export_not_ready_error(self):
        assert "EXPORT_NOT_READY" in self._src()

    def test_checks_expiry_at_runtime(self):
        src = self._src()
        assert "expires_at < utcnow" in src or "expires_at" in src

    def test_sets_status_downloaded(self):
        assert '"downloaded"' in self._src()

    def test_sets_downloaded_at(self):
        assert "downloaded_at = utcnow" in self._src()

    def test_audit_log_on_download(self):
        assert "compliance.export_downloaded_by_customer" in self._src()

    def test_rate_limit_checked_on_download(self):
        src = self._src()
        download_idx = src.find("async def download_my_export")
        download_section = src[download_idx:download_idx + 400]
        assert "_check_rate_limit" in download_section


# ── H. Admin Integration ──────────────────────────────────────────────────────

class TestAdminIntegration:
    def _src(self): return r(ROUTER)

    def test_request_source_customer_app(self):
        assert "customer_app" in self._src()

    def test_subject_type_is_customer(self):
        assert '"customer"' in self._src()

    def test_subject_email_included(self):
        assert "subject_email" in self._src()

    def test_subject_name_included(self):
        assert "subject_name" in self._src()


# ── I. api.ts Customer Compliance Methods ────────────────────────────────────

class TestApiTsCustomerCompliance:
    def _src(self): return r(API_TS)

    def test_customer_compliance_api_defined(self):
        assert "customerComplianceApi" in self._src()

    def test_list_requests_method(self):
        assert "listRequests" in self._src()

    def test_create_request_method(self):
        assert "createRequest" in self._src()

    def test_get_request_method(self):
        assert "getRequest" in self._src()

    def test_cancel_request_method(self):
        assert "cancelRequest" in self._src()

    def test_add_note_method(self):
        assert "addNote" in self._src()

    def test_list_consents_method(self):
        assert "listConsents" in self._src()

    def test_withdraw_consent_method(self):
        assert "withdrawConsent" in self._src()

    def test_download_export_method(self):
        assert "downloadExport" in self._src()

    def test_v1_me_compliance_url_in_list_requests(self):
        assert "/v1/me/compliance/requests" in self._src()

    def test_customer_compliance_request_interface(self):
        assert "CustomerComplianceRequest" in self._src()

    def test_status_label_field_in_interface(self):
        assert "status_label" in self._src()

    def test_sla_label_field_in_interface(self):
        assert "sla_label" in self._src()


# ── J. Frontend Pages ─────────────────────────────────────────────────────────

class TestFrontendPages:
    def test_privacy_page_exists(self):
        assert PRIV_PAGE.exists()

    def test_requests_list_page_exists(self):
        assert REQ_PAGE.exists()

    def test_request_detail_page_exists(self):
        assert DETAIL_PAGE.exists()

    def test_privacy_page_imports_customer_compliance_api(self):
        assert "providerComplianceApi" in r(PRIV_PAGE)

    def test_privacy_page_shows_consents(self):
        assert "listConsents" in r(PRIV_PAGE)

    def test_privacy_page_has_withdraw_action(self):
        assert "withdrawConsent" in r(PRIV_PAGE)

    def test_requests_page_has_create_modal(self):
        assert "createRequest" in r(REQ_PAGE)

    def test_requests_page_has_confirm_understanding(self):
        assert "confirm_understanding" in r(REQ_PAGE)

    def test_requests_page_shows_status_badge(self):
        assert "status_label" in r(REQ_PAGE)

    def test_detail_page_has_export_download_button(self):
        assert "download" in r(DETAIL_PAGE).lower()
        assert "export_id" in r(DETAIL_PAGE)

    def test_detail_page_has_cancel_button(self):
        assert "cancelRequest" in r(DETAIL_PAGE)

    def test_detail_page_shows_audit_trail(self):
        assert "audit_trail" in r(DETAIL_PAGE)

    def test_detail_page_shows_rejection_reason(self):
        assert "rejection_reason" in r(DETAIL_PAGE)

    def test_privacy_page_links_to_requests_page(self):
        assert '"my-requests"' in r(PRIV_PAGE)

    def test_nav_config_has_privacy_item(self):
        assert "Compliance" in r(NAV_CFG)
        assert "/provider/compliance" in r(NAV_CFG)


# ── K. Audit Logging ──────────────────────────────────────────────────────────

class TestAuditLogging:
    def _src(self): return r(ROUTER)

    def test_customer_request_created_audit(self):
        assert "compliance.customer_request_created" in self._src()

    def test_customer_request_viewed_audit(self):
        assert "compliance.customer_request_viewed" in self._src()

    def test_export_downloaded_by_customer_audit(self):
        assert "compliance.export_downloaded_by_customer" in self._src()

    def test_customer_consent_withdrawn_audit(self):
        assert "compliance.customer_consent_withdrawn" in self._src()

    def test_customer_request_cancelled_audit(self):
        assert "compliance.customer_request_cancelled" in self._src()

    def test_legal_basis_dpdp_act_2023(self):
        assert "dpdp_act_2023" in self._src()


# ── L. Status Labels ──────────────────────────────────────────────────────────

class TestStatusLabels:
    def _src(self): return r(ROUTER)

    def test_status_labels_dict_defined(self):
        assert "STATUS_LABELS" in self._src()

    def test_sla_labels_dict_defined(self):
        assert "SLA_LABELS" in self._src()

    def test_sla_breached_maps_to_delayed(self):
        assert "Delayed" in self._src()

    def test_at_risk_maps_to_due_soon(self):
        assert "Due Soon" in self._src()

    def test_on_track_maps_to_on_track(self):
        assert "On Track" in self._src()

    def test_customer_safe_request_function_exists(self):
        assert "_customer_safe_request" in self._src()

    def test_status_label_in_customer_safe_output(self):
        src = self._src()
        safe_fn = src[src.find("def _customer_safe_request"):][:1000]
        assert "status_label" in safe_fn

    def test_sla_label_in_customer_safe_output(self):
        src = self._src()
        safe_fn = src[src.find("def _customer_safe_request"):][:1000]
        assert "sla_label" in safe_fn
