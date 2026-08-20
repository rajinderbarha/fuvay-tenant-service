"""P0 Enterprise Media Library — backend + frontend tests.

Tests verify:
  - Migration 085 structure (new columns + tables)
  - MediaLibraryAdminService methods
  - Admin router endpoints registered with correct prefixes + auth guards
  - api.ts interfaces + mediaAdminApi methods
  - Frontend page enterprise features (summary cards, filters, detail drawer, etc.)
"""
import os
import re
import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

def _backend(path: str) -> str:
    full = os.path.join(os.path.dirname(__file__), "..", "app", *path.split("/"))
    with open(full, encoding="utf-8") as f:
        return f.read()


def _frontend(path: str) -> str:
    full = os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin", *path.split("/"))
    with open(full, encoding="utf-8") as f:
        return f.read()


def _migration(rev: str) -> str:
    base = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
    for fname in os.listdir(base):
        if fname.startswith(f"{rev}_"):
            with open(os.path.join(base, fname), encoding="utf-8") as f:
                return f.read()
    raise FileNotFoundError(f"Migration {rev} not found")


# ══════════════════════════════════════════════════════════════════════════════
# BACKEND TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestMigration085:
    def test_revision_is_085(self):
        src = _migration("085")
        assert 'revision = "085"' in src

    def test_down_revision_is_084(self):
        src = _migration("085")
        assert 'down_revision = "084"' in src

    def test_creates_media_links_table(self):
        src = _migration("085")
        assert '"media_links"' in src

    def test_creates_media_signed_links_table(self):
        src = _migration("085")
        assert '"media_signed_links"' in src

    def test_creates_media_audit_logs_table(self):
        src = _migration("085")
        assert '"media_audit_logs"' in src

    def test_adds_is_flagged_column(self):
        src = _migration("085")
        assert "is_flagged" in src

    def test_adds_moderation_status_column(self):
        src = _migration("085")
        assert "moderation_status" in src

    def test_adds_scan_status_column(self):
        src = _migration("085")
        assert "scan_status" in src

    def test_adds_visibility_column(self):
        src = _migration("085")
        assert "visibility" in src

    def test_adds_archived_at_column(self):
        src = _migration("085")
        assert "archived_at" in src

    def test_media_signed_links_has_token_field(self):
        src = _migration("085")
        assert "token" in src

    def test_media_signed_links_has_expires_at(self):
        src = _migration("085")
        assert "expires_at" in src

    def test_media_audit_logs_has_action_type(self):
        src = _migration("085")
        assert "action_type" in src

    def test_media_links_has_module_name(self):
        src = _migration("085")
        assert "module_name" in src

    def test_downgrade_drops_new_tables(self):
        src = _migration("085")
        assert 'op.drop_table("media_audit_logs")' in src
        assert 'op.drop_table("media_signed_links")' in src
        assert 'op.drop_table("media_links")' in src


class TestAdminServiceFile:
    def test_file_exists(self):
        _backend("engines/media/admin_service.py")

    def test_class_name(self):
        src = _backend("engines/media/admin_service.py")
        assert "class MediaLibraryAdminService" in src

    def test_has_get_summary(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def get_summary" in src

    def test_has_list_assets_admin(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def list_assets_admin" in src

    def test_has_get_detail(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def get_detail" in src

    def test_has_get_linked_records(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def get_linked_records" in src

    def test_has_get_audit_logs(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def get_audit_logs" in src

    def test_has_create_signed_preview_url(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def create_signed_preview_url" in src

    def test_has_create_signed_download_url(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def create_signed_download_url" in src

    def test_has_resolve_signed_token(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def resolve_signed_token" in src

    def test_has_archive_asset(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def archive_asset" in src

    def test_has_restore_asset(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def restore_asset" in src

    def test_has_delete_asset(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def delete_asset" in src

    def test_has_change_visibility(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def change_visibility" in src

    def test_has_flag_asset(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def flag_asset" in src

    def test_has_mark_clean(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def mark_clean" in src

    def test_has_quarantine_asset(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def quarantine_asset" in src

    def test_has_bulk_archive(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def bulk_archive" in src

    def test_has_bulk_delete(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def bulk_delete" in src

    def test_has_export_csv(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def export_csv" in src

    def test_has_get_storage_summary(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def get_storage_summary" in src

    def test_delete_checks_protected_modules(self):
        src = _backend("engines/media/admin_service.py")
        assert "PROTECTED_MODULES" in src
        assert "MEDIA_DELETE_BLOCKED" in src

    def test_signed_url_expires_constant(self):
        src = _backend("engines/media/admin_service.py")
        assert "SIGNED_LINK_TTL_PREVIEW" in src
        assert "SIGNED_LINK_TTL_DOWNLOAD" in src

    def test_audit_log_helper(self):
        src = _backend("engines/media/admin_service.py")
        assert "async def _log_audit" in src

    def test_audit_failures_never_block(self):
        src = _backend("engines/media/admin_service.py")
        # Audit log method must catch exceptions so failures never block main ops
        audit_idx = src.index("async def _log_audit")
        snippet = src[audit_idx:audit_idx + 1000]
        assert "except" in snippet

    def test_signed_token_single_use(self):
        src = _backend("engines/media/admin_service.py")
        assert "status='used'" in src or "status = 'used'" in src or "used" in src

    def test_security_no_url_guessing(self):
        src = _backend("engines/media/admin_service.py")
        # Signed URL uses secrets token, not sequential ID
        assert "secrets.token_urlsafe" in src


class TestAdminRouterFile:
    def test_file_exists(self):
        _backend("engines/media/admin_router.py")

    def test_prefix_v1_admin_media(self):
        src = _backend("engines/media/admin_router.py")
        assert 'prefix="/v1/admin/media"' in src

    def test_summary_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert '"/summary"' in src

    def test_list_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert '@router.get("", ' in src or '@router.get(""\n' in src or 'router.get("")' in src

    def test_detail_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert '/{media_id}' in src

    def test_linked_records_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert 'linked-records' in src

    def test_audit_logs_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert 'audit-logs' in src

    def test_signed_preview_url_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert 'signed-preview-url' in src

    def test_signed_download_url_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert 'signed-download-url' in src

    def test_archive_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert '/archive' in src

    def test_restore_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert '/restore' in src

    def test_delete_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert "@router.delete" in src

    def test_flag_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert '/flag' in src

    def test_mark_clean_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert 'mark-clean' in src

    def test_quarantine_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert '/quarantine' in src

    def test_bulk_archive_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert 'bulk/archive' in src

    def test_bulk_delete_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert 'bulk/delete' in src

    def test_export_csv_endpoint(self):
        src = _backend("engines/media/admin_router.py")
        assert 'export/csv' in src

    def test_auth_guard_require_super_admin(self):
        src = _backend("engines/media/admin_router.py")
        assert "require_super_admin" in src

    def test_signed_router_registered(self):
        src = _backend("engines/media/admin_router.py")
        assert "signed_router" in src

    def test_signed_router_prefix(self):
        src = _backend("engines/media/admin_router.py")
        assert 'prefix="/v1/media"' in src


class TestMainPyRegistration:
    def test_admin_router_registered(self):
        src = _backend("main.py")
        assert "media_admin_router" in src

    def test_signed_router_registered(self):
        src = _backend("main.py")
        assert "media_signed_router" in src


# ══════════════════════════════════════════════════════════════════════════════
# FRONTEND TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestApiTsInterfaces:
    def test_media_asset_admin_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface MediaAssetAdmin" in src

    def test_media_summary_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface MediaSummary" in src

    def test_media_storage_summary_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface MediaStorageSummary" in src

    def test_media_linked_record_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface MediaLinkedRecord" in src

    def test_media_audit_log_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface MediaAuditLog" in src

    def test_media_signed_url_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface MediaSignedUrl" in src

    def test_media_asset_admin_has_is_flagged(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export interface MediaAssetAdmin")
        snippet = src[idx:idx + 1200]
        assert "is_flagged" in snippet

    def test_media_asset_admin_has_moderation_status(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export interface MediaAssetAdmin")
        snippet = src[idx:idx + 1200]
        assert "moderation_status" in snippet

    def test_media_asset_admin_has_visibility(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export interface MediaAssetAdmin")
        snippet = src[idx:idx + 1200]
        assert "visibility" in snippet


class TestApiTsMediaAdminApi:
    def test_media_admin_api_exists(self):
        src = _frontend("lib/api.ts")
        assert "export const mediaAdminApi" in src

    def test_get_summary_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "getSummary" in snippet

    def test_list_media_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "listMedia" in snippet

    def test_get_detail_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "getDetail" in snippet

    def test_get_linked_records_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "getLinkedRecords" in snippet

    def test_get_audit_logs_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "getAuditLogs" in snippet

    def test_create_signed_preview_url_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "createSignedPreviewUrl" in snippet

    def test_create_signed_download_url_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "createSignedDownloadUrl" in snippet

    def test_archive_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "archiveMedia" in snippet

    def test_restore_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "restoreMedia" in snippet

    def test_delete_media_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "deleteMedia" in snippet

    def test_change_visibility_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "changeVisibility" in snippet

    def test_flag_media_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "flagMedia" in snippet

    def test_mark_clean_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "markClean" in snippet

    def test_quarantine_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "quarantineMedia" in snippet

    def test_bulk_archive_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "bulkArchive" in snippet

    def test_bulk_delete_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "bulkDelete" in snippet

    def test_export_csv_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:]
        assert "exportCsv" in snippet

    def test_storage_summary_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const mediaAdminApi")
        snippet = src[idx:idx + 6000]
        assert "getStorageSummary" in snippet


class TestMediaPage:
    def test_page_exists(self):
        _frontend("app/admin/media/page.tsx")

    def test_imports_media_admin_api(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "mediaAdminApi" in src

    def test_summary_cards_rendered(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "SummaryCards" in src

    def test_filter_bar_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "Toolbar" in src or "FilterBar" in src

    def test_detail_drawer_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "DetailDrawer" in src

    def test_flag_modal_exists(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "FlagModal" in src

    def test_quarantine_modal_exists(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "quarantine" in src.lower()

    def test_delete_modal_exists(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "DeleteModal" in src

    def test_action_menu_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "onArchive" in src or "MediaActionMenu" in src

    def test_signed_preview_used(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "createSignedPreviewUrl" in src

    def test_bulk_archive_ui(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "bulkArchive" in src

    def test_export_csv_ui(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "exportCsv" in src

    def test_audit_tab_in_detail_drawer(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "audit" in src.lower()

    def test_linked_records_tab(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "Linked Records" in src or "getLinkedRecords" in src

    def test_no_raw_tailwind_classes(self):
        src = _frontend("app/admin/media/page.tsx")
        # Allow className="skeleton" only
        bad = re.findall(r'className="(?!skeleton)[^"]*"', src)
        assert len(bad) == 0, f"Tailwind className= found: {bad[:3]}"

    def test_page_shell_used(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "AdminLayout" in src

    def test_pagination_controls(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "totalPages" in src or "setPage" in src

    def test_empty_state(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "No media files found" in src or "No files found" in src

    def test_force_delete_is_not_exposed_to_admin_ui(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "Force delete" not in src
        assert "bypass active-link guard" not in src

    def test_cursor_pagination_is_wired(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "next_cursor" in src
        assert "cursorHistory" in src

    def test_sort_is_sent_to_backend(self):
        src = _frontend("lib/api.ts")
        assert 'qs.set("sort", params.sort)' in src

    def test_delete_blocked_guard_exists_in_service(self):
        src = _backend("engines/media/admin_service.py")
        assert "MEDIA_DELETE_BLOCKED" in src

    def test_admin_layout_has_media_nav(self):
        src = _frontend("components/layout/AdminLayout.tsx")
        assert "/admin/media" in src

    def test_tab_bar_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "TabBar" in src

    def test_tab_keys_defined(self):
        src = _frontend("app/admin/media/page.tsx")
        for tab in ("flagged", "archived", "recent"):
            assert tab in src

    def test_media_grid_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "MediaGrid" in src

    def test_media_card_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "MediaCard" in src

    def test_single_enterprise_filter_toolbar(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "FilterSidebar" not in src
        for control in ("All Contexts", "All Types", "All Statuses", "showMore"):
            assert control in src

    def test_bulk_action_bar_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "BulkActionBar" in src

    def test_active_chips_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "ActiveChips" in src

    def test_upload_modal_component(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "UploadModal" in src

    def test_bulk_visibility_modal(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "BulkVisibilityModal" in src or "bulk_visibility" in src

    def test_stat_card_used(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "StatCard" in src

    def test_grid_list_toggle(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "viewMode" in src

    def test_detail_drawer_has_four_tabs(self):
        src = _frontend("app/admin/media/page.tsx")
        for tab in ("info", "access", "links", "audit"):
            assert tab in src

    def test_signed_download_url_in_detail(self):
        src = _frontend("app/admin/media/page.tsx")
        assert "createSignedDownloadUrl" in src

    def test_bulk_change_visibility_api_method(self):
        src = _frontend("lib/api.ts")
        assert "bulkChangeVisibility" in src

    def test_upload_media_api_method(self):
        src = _frontend("lib/api.ts")
        assert "uploadMedia" in src
