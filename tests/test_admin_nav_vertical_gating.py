"""The sidebar shows the verticals this deployment actually runs.

`isNavItemVisible` was a stub returning true unconditionally, while comments
throughout AdminLayout described the gating as though it worked. Every
vertical's console therefore rendered in every deployment: with only
home_services enabled, an admin was still offered Real Estate and Coaching
menus for verticals no tenant is on.

The backend has always supplied the answer -- `enabled_vertical_keys` and
`operation_visibility` on the effective-menu resolver. Nothing read them.
"""
from __future__ import annotations

import pathlib
import re

NAV = pathlib.Path("frontend/super-admin/components/layout/AdminLayout.tsx")


def _src() -> str:
    return NAV.read_text(encoding="utf-8")


def _map_body(name: str) -> str:
    """Just the object literal for `name` -- not the comments around it, which
    legitimately mention the very strings these tests assert are absent."""
    src = _src()
    start = src.index(f"const {name}")
    start = src.index("{", start)
    return src[start:src.index("};", start)]


class TestTheGateIsRealAndApplied:
    def test_it_is_no_longer_an_unconditional_true(self):
        src = _src()
        body_start = src.index("function isNavItemVisible(")
        body = src[body_start:body_start + 1200]
        # The stub was: if (!effectiveMenu) return true; return true;
        assert "OPERATION_SCOPED_NAV[itemId]" in body
        assert "operation_visibility" in body

    def test_it_is_actually_called_when_rendering(self):
        """A correct gate nobody calls changes nothing."""
        src = _src()
        assert "filter(item => isNavItemVisible(item.id, effectiveMenu))" in src

    def test_a_loading_menu_shows_items(self):
        """Hiding while the fetch is in flight would flicker the whole sidebar."""
        src = _src()
        body_start = src.index("function isNavItemVisible(")
        body = src[body_start:body_start + 1200]
        assert "if (!effectiveMenu) return true;" in body


class TestPerVerticalSectionsWereAlreadyGated:
    def test_disabled_verticals_contribute_no_section(self):
        """The per-vertical menus are injected by VerticalCatalogSection, which
        filters on is_enabled -- so a disabled vertical never renders a menu.
        No vertical-name map is needed, and adding one would be dead weight
        keyed on nav ids that do not exist."""
        assert "verticals.filter(v => v.is_enabled)" in _src()

    def test_no_vertical_name_map_was_left_behind(self):
        assert "VERTICAL_SCOPED_NAV" not in _src()


class TestOperationScopedMenus:
    def test_bookability_follows_the_field_ops_capability(self):
        block = _map_body("OPERATION_SCOPED_NAV")
        assert "jobs_field_ops" in block

    def test_capabilities_are_not_keyed_on_a_vertical_name(self):
        """Keyed on the capability so a second field-ops vertical works without
        a code change -- the reason the backend resolves these itself."""
        block = _map_body("OPERATION_SCOPED_NAV")
        assert "home_services" not in block


class TestTheBackendSuppliesTheAnswer:
    def test_the_resolver_returns_both_signals(self):
        """Guards against the fields being dropped server-side, which would
        silently return the sidebar to showing everything."""
        import inspect
        from app.engines.vertical_catalog import service as nav
        src = inspect.getsource(nav)
        assert "enabled_vertical_keys" in src
        assert "operation_visibility" in src
