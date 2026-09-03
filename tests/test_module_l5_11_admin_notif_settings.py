"""MODULE-L5-11 — the admin notification settings page/endpoints that were missing."""
import inspect, os


def test_admin_preference_endpoints_exist():
    """The admin side had no notification settings at all — only providers could
    manage which events/channels they receive. Added admin GET/PUT preferences,
    scoped to the logged-in admin, reusing the per-(user,event,channel) model."""
    router = open(os.path.join(os.path.dirname(__file__), "..", "app", "engines",
                  "platform_notifications", "admin_router.py"), encoding="utf-8").read()
    assert '@admin_notif_router.get("/preferences"' in router
    assert '@admin_notif_router.put("/preferences"' in router
    assert "get_preferences" in router and "update_preference" in router


def test_settings_page_and_nav_exist():
    root = os.path.join(os.path.dirname(__file__), "..")
    workspace = os.path.join(root, "frontend", "super-admin", "app", "admin",
                             "notifications", "page.tsx")
    assert os.path.isfile(workspace)
    page = open(workspace, encoding="utf-8").read()
    assert "NotificationSettingsPanel" in page
    assert 'key: "settings"' in page
    api = open(os.path.join(root, "frontend", "super-admin", "lib", "api.ts"), encoding="utf-8").read()
    assert "getPreferences" in api and "updatePreference" in api
    nav = open(os.path.join(root, "frontend", "super-admin", "components", "layout",
               "AdminLayout.tsx"), encoding="utf-8").read()
    assert 'href: "/admin/notifications"' in nav
    assert "/admin/notifications/settings" not in nav
