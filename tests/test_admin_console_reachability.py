"""The admin console must be able to reach what it governs.

Two failure modes, both found live in this console and both invisible until
someone goes looking:

  a router built but never mounted   -- the feature 404s for every app;
  a page built but never linked      -- the feature works and nobody can find it.

Legal documents had BOTH at once: the engine, an admin console and consumers in
the customer app, the staff app and the tenant portal, with neither router
mounted and no sidebar entry. The one surface that controls what every app
shows its users was unreachable twice over.
"""
from __future__ import annotations

import inspect
import pathlib
import re

NAV = pathlib.Path("frontend/super-admin/components/layout/AdminLayout.tsx")


def _nav_hrefs() -> set[str]:
    return set(re.findall(r'href:\s*"(/admin[^"]*)"', NAV.read_text(encoding="utf-8")))


class TestLegalDocumentsAreMounted:
    def test_both_routers_are_mounted(self):
        from app import main
        src = inspect.getsource(main)
        assert "legal_admin_router" in src
        assert "legal_public_router" in src

    def test_the_admin_console_is_linked(self):
        assert "/admin/legal" in _nav_hrefs()

    def test_every_app_has_a_consumer(self):
        """Mounting only mattered because all three were already waiting on it."""
        for consumer in (
            "mobile/customer-app/src/api/legalDocuments",
            "mobile/staff-app/src/services/legal",
            "frontend/tenant-portal/lib/api-legal.ts",
        ):
            assert pathlib.Path(consumer).exists(), consumer


class TestOrphanedConsolesAreLinked:
    """Built, working consoles must be reachable from the sidebar."""

    def test_support_queue_is_linked(self):
        # A provider could raise a support request no admin would ever see.
        assert "/admin/support" in _nav_hrefs()

class TestNoRouterIsLeftUnmounted:
    def test_every_engine_router_is_mounted(self):
        """The audit script that found the legal engine, run as a test.

        This class of bug has appeared three times in this codebase: a complete
        engine with a console and consumers, absent from _mount_routers, 404ing
        silently because the callers fail soft.
        """
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "scripts/audit_unmounted_routers.py"],
            capture_output=True, text=True, timeout=300,
        )
        out = result.stdout
        # The script prints "N potentially unmounted router files"
        match = re.search(r"(\d+) potentially unmounted router files", out)
        assert match, f"audit did not report a count:\n{out}"
        assert match.group(1) == "0", f"unmounted routers found:\n{out}"


class TestTheDeadNavConfigIsGone:
    def test_the_drifted_nav_map_was_deleted(self):
        """`lib/nav-config.ts` was referenced only in comments, and its own
        neighbours documented it as out of sync. It survived long enough to
        send this audit down the wrong path before being checked."""
        assert not pathlib.Path("frontend/super-admin/lib/nav-config.ts").exists()

    def test_the_sidebar_is_the_single_nav_authority(self):
        assert NAV.exists()
        assert len(_nav_hrefs()) > 20
