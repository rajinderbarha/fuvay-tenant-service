"""P0 Enterprise Notification Template Center — frontend checks.

Static source-inspection tests (consistent with other page-redesign suites in
this repo) verifying the flat-list-only page and Type/Channel/Title/Body modal
were replaced with an enterprise summary/table/wizard/preview/test-send/
versions UI backed by the real admin API (no mock data).
"""
import os

# NOTE: /admin/notifications is now a separate notification feed/inbox page
# (mark-read/mark-all-read UI, sprint27AdminApi). The Enterprise Template
# Center this suite verifies lives at the templates/ subpage.
PAGE = os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin", "app", "admin", "notifications", "templates", "page.tsx")
API_TS = os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin", "lib", "api.ts")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestApiClient:
    def test_admin_api_defines_all_endpoints(self):
        src = _read(API_TS)
        for method in [
            "listTemplates", "getSummary", "createTemplate", "updateTemplate", "activate",
            "deactivate", "archive", "deleteTemplate", "clone", "createOverride", "validate",
            "renderPreview", "testSend", "listVersions", "rollback", "deliveryAnalytics",
            "listAuditLogs", "seedDefaultsPreview", "seedDefaults", "resolveEffectiveTemplate",
        ]:
            assert f"{method}:" in src, f"notifTemplateAdminApi missing method: {method}"


class TestPageStructure:
    def test_page_no_longer_flat_list_only(self):
        src = _read(PAGE)
        assert "TemplateRow" not in src
        assert "NOTIF_TYPES" not in src  # old hardcoded list replaced by EVENT_TYPES

    def test_summary_cards_present(self):
        src = _read(PAGE)
        for label in ["Total Templates", "Active", "Drafts", "Platform Defaults",
                      "Tenant Overrides", "Validation Errors", "Failed Deliveries", "Missing Translations"]:
            assert label in src

    def test_tabs_present(self):
        src = _read(PAGE)
        for label in ["All Templates", "Platform Defaults", "Vertical Templates",
                      "Tenant Overrides", "Drafts", "Audit Logs"]:
            assert f'label: "{label}"' in src or f'"{label}"' in src

    def test_toolbar_has_filters(self):
        src = _read(PAGE)
        assert "eventFilter" in src and "channelFilter" in src and "search" in src

    def test_table_replaces_plain_list(self):
        src = _read(PAGE)
        assert "<DataTable" in src

    def test_create_wizard_has_multiple_steps(self):
        src = _read(PAGE)
        assert "CreateTemplateWizard" in src
        for step in ["Basic Details", "Audience & Scope", "Channel Content", "Review & Publish"]:
            assert step in src

    def test_platform_defaults_have_no_delete_action(self):
        src = _read(PAGE)
        assert "!row.is_platform_default && row.status !== \"active\"" in src

    def test_seed_defaults_dialog_present(self):
        src = _read(PAGE)
        assert "seedOpen" in src and "Seed Default Templates" in src

    def test_detail_drawer_has_preview_and_test_send(self):
        src = _read(PAGE)
        assert "TemplateDetailDrawer" in src
        assert "Generate Preview" in src
        assert "Send Test" in src

    def test_detail_drawer_has_version_history_tab(self):
        src = _read(PAGE)
        assert '"versions"' in src

    def test_test_send_recipient_field_present(self):
        src = _read(PAGE)
        assert "Test Recipient" in src

    def test_detail_drawer_has_delivery_analytics_tab(self):
        src = _read(PAGE)
        assert '"analytics"' in src
        assert "deliveryAnalytics" in src
        assert "AnalyticsStat" in src

    def test_uses_real_admin_api_not_basic_notificationApi(self):
        src = _read(PAGE)
        assert "notifTemplateAdminApi" in src

    def test_empty_state_not_giant_blank_box(self):
        src = _read(PAGE)
        assert "EmptyState" in src
        assert "No templates found" in src
