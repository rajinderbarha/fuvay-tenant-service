"""Canonical notification-center and runtime-template frontend checks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REDIRECT = ROOT / "frontend/super-admin/app/admin/notifications/templates/page.tsx"
CENTER = ROOT / "frontend/super-admin/app/admin/notifications/page.tsx"
PANEL = ROOT / "frontend/super-admin/app/admin/notifications/RuntimeTemplatesPanel.tsx"
API = ROOT / "frontend/super-admin/lib/api.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_legacy_template_url_redirects_to_canonical_center():
    assert 'redirect("/admin/notifications?tab=templates")' in _read(REDIRECT)


def test_notification_center_registers_templates_tab():
    src = _read(CENTER)
    assert 'key: "templates"' in src
    assert "RuntimeTemplatesPanel" in src


def test_runtime_templates_use_real_api_and_filters():
    src = _read(PANEL)
    assert "sprint27AdminApi.listTemplates" in src
    assert "search" in src and "channel" in src
    assert "No runtime templates match" in src


def test_runtime_templates_support_edit_and_state_change():
    src = _read(PANEL)
    assert "Edit" in src
    assert "Disable" in src and "Enable" in src
    assert "action_url_template" in src


def test_notification_api_client_is_real():
    src = _read(API)
    assert "sprint27AdminApi" in src
    for method in ("listTemplates", "createTemplate", "updateTemplate", "activateTemplate", "deactivateTemplate"):
        assert method in src
