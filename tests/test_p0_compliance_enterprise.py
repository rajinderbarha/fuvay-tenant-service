"""P0 Enterprise DPDP Act 2023 Compliance Module — Test Suite.

Tests cover:
  A. Migration 079 — table structure
  B. Models — ComplianceRequest / ComplianceRequestItem / ComplianceExport
  C. Enterprise service — summary, CRUD, scan, approve, reject, process
  D. Admin router — all endpoint routes present
  E. api.ts — enterprise types and methods
  F. Frontend page — tabs, components, actions
  G. SLA logic
  H. Retention / exemption rules
  I. Consent registry
  J. Audit trail
"""
import ast
import importlib
import inspect
import os
import re
import textwrap
from pathlib import Path

import pytest

ROOT   = Path(__file__).parent.parent
MODELS = ROOT / "app" / "engines" / "compliance" / "models.py"
SVC    = ROOT / "app" / "engines" / "compliance" / "enterprise_service.py"
ROUTER = ROOT / "app" / "engines" / "compliance" / "admin_router.py"
MIG    = ROOT / "alembic" / "versions" / "079_compliance_enterprise_upgrade.py"
API_TS = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
PAGE   = ROOT / "frontend" / "super-admin" / "app" / "admin" / "compliance" / "page.tsx"


# ── A. Migration 079 ──────────────────────────────────────────────────────────

class TestMigration079:
    def test_migration_file_exists(self):
        assert MIG.exists(), "Migration 079 not found"

    def test_revision(self):
        src = MIG.read_text()
        assert 'revision = "079"' in src

    def test_down_revision(self):
        src = MIG.read_text()
        assert 'down_revision = "078"' in src

    def test_compliance_requests_table(self):
        src = MIG.read_text()
        assert '"compliance_requests"' in src

    def test_compliance_request_items_table(self):
        src = MIG.read_text()
        assert '"compliance_request_items"' in src

    def test_compliance_exports_table(self):
        src = MIG.read_text()
        assert '"compliance_exports"' in src

    def test_request_number_unique(self):
        src = MIG.read_text()
        assert "request_number" in src
        assert "unique=True" in src

    def test_request_items_cascade_fk(self):
        src = MIG.read_text()
        assert "CASCADE" in src

    def test_exports_setnull_fk(self):
        src = MIG.read_text()
        assert "SET NULL" in src

    def test_sla_status_column(self):
        src = MIG.read_text()
        assert "sla_status" in src

    def test_verification_status_column(self):
        src = MIG.read_text()
        assert "verification_status" in src

    def test_subject_type_column(self):
        src = MIG.read_text()
        assert "subject_type" in src

    def test_indexes_created(self):
        src = MIG.read_text()
        assert "op.create_index" in src
        assert "ix_compliance_requests_status" in src
        assert "ix_compliance_requests_sla" in src

    def test_downgrade_drops_tables(self):
        src = MIG.read_text()
        assert "op.drop_table" in src
        assert '"compliance_exports"' in src


# ── B. Models ─────────────────────────────────────────────────────────────────

class TestModels:
    def _src(self):
        return MODELS.read_text()

    def test_compliance_request_class(self):
        assert "class ComplianceRequest" in self._src()

    def test_compliance_request_item_class(self):
        assert "class ComplianceRequestItem" in self._src()

    def test_compliance_export_class(self):
        assert "class ComplianceExport" in self._src()

    def test_request_number_field(self):
        assert "request_number" in self._src()

    def test_sla_status_field(self):
        src = self._src()
        assert src.count("sla_status") >= 2  # migration + model

    def test_verification_status_field(self):
        assert "verification_status" in self._src()

    def test_subject_type_field(self):
        assert "subject_type" in self._src()

    def test_request_item_planned_action(self):
        assert "planned_action" in self._src()

    def test_request_item_exemption_reason(self):
        assert "exemption_reason" in self._src()

    def test_export_download_url(self):
        assert "download_url" in self._src()

    def test_to_dict_methods(self):
        src = self._src()
        assert src.count("def to_dict") >= 3

    def test_fk_imports_updated(self):
        assert "ForeignKey" in self._src()

    def test_original_models_preserved(self):
        src = self._src()
        assert "class ConsentRecord" in src
        assert "class DataDeletionRequest" in src
        assert "class ComplianceAuditLog" in src


# ── C. Enterprise Service ─────────────────────────────────────────────────────

class TestEnterpriseService:
    def _src(self):
        return SVC.read_text()

    def test_file_exists(self):
        assert SVC.exists()

    def test_class_definition(self):
        assert "class ComplianceEnterpriseService" in self._src()

    def test_get_enterprise_summary(self):
        assert "async def get_enterprise_summary" in self._src()

    def test_summary_returns_10_fields(self):
        src = self._src()
        for field in ["pending_erasure", "pending_export", "pending_consent_withdrawal",
                      "pending_verification", "sla_breached", "sla_at_risk",
                      "completed_this_month", "rejected_total", "exemptions_applied",
                      "consent_records", "compliance_status"]:
            assert field in src, f"Missing summary field: {field}"

    def test_list_requests(self):
        assert "async def list_requests" in self._src()

    def test_create_request(self):
        assert "async def create_request" in self._src()

    def test_get_request(self):
        assert "async def get_request" in self._src()

    def test_verify_identity(self):
        assert "async def verify_identity" in self._src()

    def test_scan_data(self):
        assert "async def scan_data" in self._src()

    def test_approve_request(self):
        assert "async def approve_request" in self._src()

    def test_reject_request(self):
        assert "async def reject_request" in self._src()

    def test_reject_requires_reason(self):
        src = self._src()
        assert "Rejection reason is required" in src or "rejection_reason" in src

    def test_apply_exemption(self):
        assert "async def apply_exemption" in self._src()

    def test_process_request(self):
        assert "async def process_request" in self._src()

    def test_get_request_audit(self):
        assert "async def get_request_audit" in self._src()

    def test_refresh_sla_statuses(self):
        assert "async def refresh_sla_statuses" in self._src()

    def test_list_exports(self):
        assert "async def list_exports" in self._src()

    def test_expire_export(self):
        assert "async def expire_export" in self._src()

    def test_list_consent_records(self):
        assert "async def list_consent_records" in self._src()

    def test_revoke_consent(self):
        assert "async def revoke_consent" in self._src()

    def test_list_retention_policies(self):
        assert "async def list_retention_policies" in self._src()

    def test_list_audit_logs(self):
        assert "async def list_audit_logs" in self._src()

    def test_data_modules_include_financial_exemptions(self):
        src = self._src()
        for module in ["Payments", "Invoices", "Wallet Ledger", "Commission Records"]:
            assert module in src, f"Missing financial module: {module}"

    def test_financial_modules_have_retain_action(self):
        src = self._src()
        assert '"action": "retain"' in src

    def test_sla_at_risk_threshold_24h(self):
        src = self._src()
        assert "< 24" in src or "hours < 24" in src

    def test_request_number_format(self):
        src = self._src()
        assert "COMP-" in src

    def test_valid_subject_types(self):
        src = self._src()
        for st in ["customer", "provider_owner", "tenant_staff", "platform_admin", "guest_user"]:
            assert st in src

    def test_valid_request_types(self):
        src = self._src()
        for rt in ["right_to_erasure", "data_export", "consent_withdrawal",
                   "data_correction", "processing_objection"]:
            assert rt in src

    def test_audit_helper_append_only(self):
        src = self._src()
        assert "self.db.add(ComplianceAuditLog" in src
        # Audit never deletes
        assert "self.db.delete(ComplianceAuditLog" not in src

    def test_scan_creates_items_for_all_modules(self):
        src = self._src()
        assert "DATA_MODULES" in src
        assert "for module in DATA_MODULES" in src

    def test_process_checks_approved_status(self):
        src = self._src()
        assert "approved" in src and "partially_approved" in src

    def test_wraps_base_compliance_service(self):
        assert "ComplianceService" in self._src()


# ── D. Admin Router ───────────────────────────────────────────────────────────

class TestAdminRouter:
    def _src(self):
        return ROUTER.read_text()

    def test_file_exists(self):
        assert ROUTER.exists()

    def test_prefix(self):
        assert 'prefix="/v1/admin/compliance"' in self._src()

    def test_summary_endpoint(self):
        assert '"/summary"' in self._src()

    def test_overview_endpoint(self):
        assert '"/overview"' in self._src()

    def test_sla_refresh_endpoint(self):
        assert '"/sla/refresh"' in self._src()

    def test_requests_list_endpoint(self):
        assert '"/requests"' in self._src()

    def test_request_detail_endpoint(self):
        assert '"/requests/{request_id}"' in self._src()

    def test_verify_identity_endpoint(self):
        assert '"/requests/{request_id}/verify-identity"' in self._src()

    def test_scan_data_endpoint(self):
        assert '"/requests/{request_id}/scan-data"' in self._src()

    def test_approve_endpoint(self):
        assert '"/requests/{request_id}/approve"' in self._src()

    def test_reject_endpoint(self):
        assert '"/requests/{request_id}/reject"' in self._src()

    def test_apply_exemption_endpoint(self):
        assert '"/requests/{request_id}/apply-exemption"' in self._src()

    def test_process_endpoint(self):
        assert '"/requests/{request_id}/process"' in self._src()

    def test_audit_endpoint(self):
        assert '"/requests/{request_id}/audit"' in self._src()

    def test_consents_list_endpoint(self):
        assert '"/consents"' in self._src()

    def test_consent_revoke_endpoint(self):
        assert '"/consents/{user_id}/revoke"' in self._src()

    def test_exports_list_endpoint(self):
        assert '"/exports"' in self._src()

    def test_exports_detail_endpoint(self):
        assert '"/exports/{export_id}"' in self._src()

    def test_export_expire_endpoint(self):
        assert '"/exports/{export_id}/expire"' in self._src()

    def test_retention_get_endpoint(self):
        assert '"/retention-policies"' in self._src()

    def test_audit_trail_endpoint(self):
        assert '"/audit-trail"' in self._src()

    def test_all_require_super_admin(self):
        src = self._src()
        assert "require_super_admin" in src

    def test_uses_enterprise_service(self):
        assert "ComplianceEnterpriseService" in self._src()

    def test_router_registered_in_main(self):
        main_src = (ROOT / "app" / "main.py").read_text()
        assert "compliance_admin_router" in main_src
        assert "admin_router" in main_src


# ── E. api.ts ─────────────────────────────────────────────────────────────────

class TestApiTs:
    def _src(self):
        return API_TS.read_text()

    def test_enterprise_summary_type(self):
        assert "ComplianceEnterpriseSummary" in self._src()

    def test_enterprise_request_type(self):
        assert "ComplianceEnterpriseRequest" in self._src()

    def test_enterprise_request_list_type(self):
        assert "ComplianceEnterpriseRequestList" in self._src()

    def test_compliance_request_item_type(self):
        assert "ComplianceRequestItem" in self._src()

    def test_consent_record_type(self):
        assert "ConsentRecord" in self._src()

    def test_consent_record_list_type(self):
        assert "ConsentRecordList" in self._src()

    def test_compliance_export_record_type(self):
        assert "ComplianceExportRecord" in self._src()

    def test_compliance_export_list_type(self):
        assert "ComplianceExportList" in self._src()

    def test_compliance_audit_list_type(self):
        assert "ComplianceAuditList" in self._src()

    def test_enterprise_summary_method(self):
        assert "enterpriseSummary" in self._src()

    def test_list_requests_method(self):
        assert "listRequests" in self._src()

    def test_create_request_method(self):
        assert "createRequest" in self._src()

    def test_get_request_method(self):
        assert "getRequest" in self._src()

    def test_verify_identity_method(self):
        assert "verifyIdentity" in self._src()

    def test_scan_data_method(self):
        assert "scanData" in self._src()

    def test_approve_request_method(self):
        assert "approveRequest" in self._src()

    def test_reject_request_method(self):
        assert "rejectRequest" in self._src()

    def test_apply_exemption_method(self):
        assert "applyExemption" in self._src()

    def test_process_request_method(self):
        assert "processRequest" in self._src()

    def test_get_request_audit_method(self):
        assert "getRequestAudit" in self._src()

    def test_list_consents_method(self):
        assert "listConsents" in self._src()

    def test_revoke_consent_method(self):
        assert "revokeConsent" in self._src()

    def test_list_exports_method(self):
        assert "listExports" in self._src()

    def test_expire_export_method(self):
        assert "expireExport" in self._src()

    def test_list_audit_trail_method(self):
        assert "listAuditTrail" in self._src()

    def test_legacy_methods_preserved(self):
        src = self._src()
        assert "listDeletionRequests" in src
        assert "processDeletion" in src
        assert "listRetentionPolicies" in src

    def test_admin_compliance_prefix(self):
        assert "/v1/admin/compliance/" in self._src()


# ── F. Frontend Page ──────────────────────────────────────────────────────────

class TestFrontendPage:
    def _src(self):
        return PAGE.read_text()

    def test_file_exists(self):
        assert PAGE.exists()

    def test_uses_enterprise_summary(self):
        assert "enterpriseSummary" in self._src()

    def test_tabs_defined(self):
        src = self._src()
        for tab in ["requests", "consent", "exports", "retention", "audit"]:
            assert tab in src

    def test_10_stat_cards(self):
        src = self._src()
        # Count StatCard occurrences
        count = src.count("<StatCard")
        assert count >= 10, f"Expected ≥10 StatCards, found {count}"

    def test_request_table_renders(self):
        assert "request_number" in self._src()

    def test_sla_status_displayed(self):
        assert "sla_status" in self._src()

    def test_verification_status_displayed(self):
        assert "verification_status" in self._src()

    def test_detail_drawer_component(self):
        assert "RequestDetailDrawer" in self._src()

    def test_scan_data_button(self):
        assert "Scan Data Modules" in self._src() or "scanData" in self._src()

    def test_approve_button(self):
        assert "Approve" in self._src()

    def test_reject_button(self):
        assert "Reject" in self._src()

    def test_process_button(self):
        assert "Process Request" in self._src()

    def test_verify_identity_button(self):
        assert "Verify Identity" in self._src()

    def test_data_inventory_items_shown(self):
        assert "Data Inventory" in self._src() or "module_name" in self._src()

    def test_exemption_reason_shown(self):
        assert "exemption_reason" in self._src()

    def test_audit_trail_shown(self):
        assert "audit_trail" in self._src() or "Audit Trail" in self._src()

    def test_consent_tab_renders(self):
        assert "Consent Records" in self._src()

    def test_exports_tab_renders(self):
        assert "Data Exports" in self._src()

    def test_retention_tab_renders(self):
        assert "Statutory Exemptions" in self._src() or "Retention Policies" in self._src()

    def test_audit_tab_renders(self):
        assert "Compliance Audit Trail" in self._src()

    def test_create_request_modal(self):
        assert "Create Compliance Request" in self._src()

    def test_filter_toolbar(self):
        src = self._src()
        assert "typeFilter" in src
        assert "statusFilter" in src
        assert "slaFilter" in src

    def test_financial_exemption_note(self):
        src = self._src()
        assert "GST Act" in src or "financial records" in src.lower()

    def test_immutable_audit_note(self):
        src = self._src()
        assert "Append-only" in src or "cannot be modified" in src

    def test_compliance_status_badge(self):
        assert "compliance_status" in self._src()

    def test_uses_request_type_label_map(self):
        assert "REQUEST_TYPE_LABEL" in self._src()

    def test_sla_overdue_highlight(self):
        assert "sla_overdue" in self._src()

    def test_admin_layout_used(self):
        assert "AdminLayout" in self._src()


# ── G. SLA Logic ─────────────────────────────────────────────────────────────

class TestSlaLogic:
    def _src(self):
        return SVC.read_text()

    def test_sla_hours_constant(self):
        assert "REQUEST_SLA_HOURS" in self._src() or "ERASURE_SLA_HOURS" in self._src()

    def test_due_at_set_at_creation(self):
        src = self._src()
        assert "due_at" in src
        assert "timedelta" in src

    def test_sla_breached_status(self):
        assert "sla_breached" in self._src() or '"breached"' in self._src()

    def test_sla_at_risk_status(self):
        assert '"at_risk"' in self._src()

    def test_refresh_sla_marks_breached(self):
        src = self._src()
        assert 'req.sla_status = "breached"' in src

    def test_refresh_sla_marks_at_risk(self):
        src = self._src()
        assert 'req.sla_status = "at_risk"' in src


# ── H. Retention / Exemption ─────────────────────────────────────────────────

class TestRetentionExemptions:
    def _src(self):
        return SVC.read_text()

    def test_financial_modules_marked_retain(self):
        src = self._src()
        assert '"action": "retain"' in src

    def test_gst_exemption_text(self):
        src = self._src()
        assert "GST" in src

    def test_audit_logs_retained(self):
        src = self._src()
        assert "platform_audit_logs" in src

    def test_wallet_retained(self):
        src = self._src()
        assert "wallet_ledger" in src

    def test_non_financial_delete_or_anonymize(self):
        src = self._src()
        assert '"anonymize"' in src
        assert '"delete"' in src

    def test_apply_exemption_changes_action_to_retain(self):
        src = self._src()
        assert '"retain"' in src and "planned_action" in src


# ── I. Consent Registry ────────────────────────────────────────────────────────

class TestConsentRegistry:
    def _src(self):
        return SVC.read_text()

    def test_list_consent_records_paginated(self):
        src = self._src()
        assert "async def list_consent_records" in src
        assert "page" in src

    def test_revoke_inserts_new_record(self):
        src = self._src()
        # revoke_consent delegates to withdraw_consent which calls record_consent (insert)
        assert "withdraw_consent" in src

    def test_consent_filter_by_type(self):
        src = self._src()
        assert "consent_type" in src


# ── J. Audit Trail ────────────────────────────────────────────────────────────

class TestAuditTrail:
    def _src(self):
        return SVC.read_text()

    def test_audit_called_on_create(self):
        src = self._src()
        assert "request.created" in src

    def test_audit_called_on_approve(self):
        src = self._src()
        assert "approved" in src

    def test_audit_called_on_reject(self):
        src = self._src()
        assert "request.rejected" in src

    def test_audit_called_on_process(self):
        src = self._src()
        assert "request.processed" in src

    def test_audit_append_only(self):
        src = self._src()
        # _audit only adds, never removes
        assert "self.db.add(ComplianceAuditLog" in src
        assert "self.db.delete(ComplianceAuditLog" not in src

    def test_audit_trail_endpoint_exists(self):
        assert '"/audit-trail"' in ROUTER.read_text()
