"""Customer-facing product branding must be Fuvay across every role surface.

Internal ``serviceos`` identifiers remain compatibility contracts: token
audiences, local-storage keys, package imports, bundle identifiers and API
error class names must not be renamed as part of a display-brand migration.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOTS = (ROOT / "app", ROOT / "frontend", ROOT / "mobile")
TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".py", ".ts", ".tsx"}
OLD_DISPLAY_BRAND = re.compile(r"(?<![A-Za-z0-9_])ServiceOS(?![A-Za-z0-9_])")
IGNORED_PARTS = {".git", ".next", "node_modules", "tests", "__tests__", "var"}
USER_INTERFACE_ROOTS = (
    ROOT / "frontend/super-admin/app",
    ROOT / "frontend/super-admin/components",
    ROOT / "frontend/tenant-portal/app",
    ROOT / "frontend/tenant-portal/components",
    ROOT / "mobile/customer-app/src",
    ROOT / "mobile/staff-app/src",
)


def _iter_source_files(source_root: Path, suffixes: set[str]):
    for current_root, directories, filenames in os.walk(source_root):
        directories[:] = [name for name in directories if name not in IGNORED_PARTS]
        root = Path(current_root)
        for filename in filenames:
            path = root / filename
            if path.suffix in suffixes:
                yield path


def test_no_old_display_brand_remains_in_production_surfaces():
    violations: list[str] = []
    for source_root in PRODUCTION_ROOTS:
        for path in _iter_source_files(source_root, TEXT_SUFFIXES):
            if OLD_DISPLAY_BRAND.search(path.read_text(encoding="utf-8")):
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_user_interfaces_do_not_expose_the_legacy_public_email_domain():
    violations: list[str] = []
    for source_root in USER_INTERFACE_ROOTS:
        for path in _iter_source_files(source_root, {".ts", ".tsx"}):
            if "@serviceos.in" in path.read_text(encoding="utf-8"):
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_four_role_product_names_are_fuvay():
    customer = json.loads((ROOT / "mobile/customer-app/app.json").read_text(encoding="utf-8"))
    staff = json.loads((ROOT / "mobile/staff-app/app.json").read_text(encoding="utf-8"))
    assert customer["expo"]["name"] == "Fuvay"
    assert staff["expo"]["name"] == "Fuvay Staff"

    package_names = {
        "customer": json.loads(
            (ROOT / "mobile/customer-app/package.json").read_text(encoding="utf-8")
        )["name"],
        "staff": json.loads(
            (ROOT / "mobile/staff-app/package.json").read_text(encoding="utf-8")
        )["name"],
        "admin": json.loads(
            (ROOT / "frontend/super-admin/package.json").read_text(encoding="utf-8")
        )["name"],
        "tenant": json.loads(
            (ROOT / "frontend/tenant-portal/package.json").read_text(encoding="utf-8")
        )["name"],
    }
    assert package_names == {
        "customer": "fuvay-customer-app",
        "staff": "fuvay-staff-app",
        "admin": "fuvay-super-admin",
        "tenant": "fuvay-tenant-portal",
    }

    admin_layout = (ROOT / "frontend/super-admin/app/layout.tsx").read_text(encoding="utf-8")
    tenant_layout = (ROOT / "frontend/tenant-portal/app/layout.tsx").read_text(encoding="utf-8")
    assert 'title: "Fuvay — Super Admin"' in admin_layout
    assert 'title: "Fuvay — Business Portal"' in tenant_layout


def test_backend_and_auth_present_fuvay_without_breaking_audiences():
    config = (ROOT / "app/config.py").read_text(encoding="utf-8")
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    auth_types = (ROOT / "mobile/staff-app/src/navigation/guards/types.ts").read_text(encoding="utf-8")
    assert 'APP_NAME: str = "Fuvay"' in config
    assert 'title="Fuvay API"' in main
    assert '"serviceos:staff"' in auth_types


def test_persisted_display_content_is_rebranded_without_rewriting_history():
    migration = (ROOT / "alembic/versions/339_fuvay_display_brand.py").read_text(encoding="utf-8")
    for table in (
        "notification_templates",
        "notif_event_templates",
        "support_knowledge_articles",
        "marketing_campaign_rules",
        "legal_document_versions",
    ):
        assert table in migration
    assert "replace(body, 'ServiceOS', 'Fuvay')" in migration
    assert "delivery_status = 'provider_not_configured'" in migration
    assert '"brand_migration":"339"' in migration
    assert "supersedes_id" in migration
