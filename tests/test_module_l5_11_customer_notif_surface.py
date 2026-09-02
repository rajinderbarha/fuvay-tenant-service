"""MODULE-L5-11 — the customer notification surface that was entirely missing."""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
APP = os.path.join(ROOT, "mobile", "customer-app", "src")


def test_customer_notification_client_and_page_exist():
    """The customer app had 6 notification endpoints and zero UI — booking
    updates, complaint responses and settlement offers were delivered with no way
    to see or manage them in the app."""
    assert os.path.isfile(os.path.join(APP, "api", "notifications", "notificationsApi.ts"))
    assert os.path.isfile(os.path.join(APP, "screens", "notifications", "NotificationCenterScreen.tsx"))


def test_client_covers_all_endpoints():
    api = open(os.path.join(APP, "api", "notifications", "notificationsApi.ts"), encoding="utf-8").read()
    for fn in ("listMyNotifications", "getMyUnreadNotificationCount",
               "markMyNotificationRead", "markAllMyNotificationsRead"):
        assert fn in api, fn


def test_page_has_inbox_and_settings_and_is_reachable():
    page = open(os.path.join(APP, "screens", "notifications", "NotificationCenterScreen.tsx"), encoding="utf-8").read()
    assert "useMarkAllNotificationsReadMutation" in page
    routes = open(os.path.join(APP, "navigation", "routeTypes.ts"), encoding="utf-8").read()
    assert "Notifications: undefined" in routes
